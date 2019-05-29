import os
import io
import sys
import time
import copy
import shutil
import inspect
import itertools
import configparser
import collections
import importlib
import utils
import gather
import traceback
import dbtypedict

from importlib.machinery import SourceFileLoader
from subprocess import Popen, PIPE
from pysixdb import SixDB

class Study(object):

    def __init__(self, name='example_study', loc=os.getcwd()):
        '''Constructor'''
        self.name = name
        self.location = os.path.abspath(loc)
        self.study_path = os.path.join(self.location, self.name)
        self.config = configparser.ConfigParser()
        self.config.optionxform = str #preserve case
        self.submission = None
        self.preprocess_joblist = []
        self.sixtrack_joblist = []
        self.db_info = {}
        #All the requested parameters for a study
        self.paths = {}
        self.env = {}
        self.madx_params = collections.OrderedDict()
        self.madx_input = {}
        self.madx_output = {}
        self.oneturn_sixtrack_params = collections.OrderedDict()
        self.oneturn_sixtrack_input = {}
        self.oneturn_sixtrack_output = []
        self.sixtrack_params = collections.OrderedDict()
        self.sixtrack_input = {}
        self.sixtrack_output = []
        self.tables = {}
        self.table_keys = {}
        self.pragma = collections.OrderedDict()
        self.boinc_vars = collections.OrderedDict()
        #initialize default values
        Study._defaults(self)
        Study._structure(self)

    def _defaults(self):
        '''initialize a study with some default settings'''
        #full path to madx
        self.paths["madx_exe"] = "/afs/cern.ch/user/m/mad/bin/madx"
        #full path to sixtrack
        self.paths["sixtrack_exe"] = "/afs/cern.ch/project/sixtrack/build/sixtrack"
        self.paths["study_path"] = self.study_path
        self.paths["preprocess_in"] = os.path.join(self.study_path, "preprocess_input")
        self.paths["preprocess_out"] = os.path.join(self.study_path, "preprocess_output")
        self.paths["sixtrack_in"] = os.path.join(self.study_path, "sixtrack_input")
        self.paths["sixtrack_out"] = os.path.join(self.study_path, "sixtrack_output")
        self.paths["gather"] = os.path.join(self.study_path, "gather")
        self.paths["templates"] = self.study_path
        self.paths["boinc_spool"] = "/afs/cern.ch/work/b/boinc/boinc"
        self.cluster_module = None
        self.cluster_name = 'HTCondor'
        self.log_file = None
        self.mes_level = 1

        self.madx_output = {
                'fc.2': 'fort.2',
                'fc.3': 'fort.3.mad',
                'fc.3.aux': 'fort.3.aux',
                'fc.8': 'fort.8',
                'fc.16': 'fort.16',
                'fc.34': 'fort.34'}
        self.oneturn_sixtrack_params = collections.OrderedDict([
                ("turnss", 1),
                ("nss", 1),
                ("ax0s", 0.1),
                ("ax1s", 0.1),
                ("imc", 1),
                ("iclo6", 2),
                ("writebins", 1),
                ("ratios", 1),
                ("Runnam", 'FirstTurn'),
                ("idfor", 0),
                ("ibtype", 0),
                ("ition", 0),
                ("CHRO", '/'),
                ("TUNE", '/'),
                ("POST", 'POST'),
                ("POS1", ''),
                ("ndafi", 1),
                ("tunex", 62.28),
                ("tuney", 60.31),
                ("inttunex", 62.28),
                ("inttuney", 60.31),
                ("DIFF", '/DIFF'),
                ("DIF1", '/'),
                ("pmass", 938.272013),
                ("emit_beam", 3.75),
                ("e0", 7000),
                ("bunch_charge", 1.15E11),
                ("CHROM", 0),
                ("chrom_eps", 0.000001),
                ("dp1", 0.000001),
                ("dp2", 0.000001),
                ("chromx", 2),
                ("chromy", 2),
                ("TUNEVAL", '/'),
                ("CHROVAL", '/')])
        self.oneturn_sixtrack_input['input'] = copy.deepcopy(self.madx_output)
        self.oneturn_sixtrack_output = ['fort.10']
        self.sixtrack_output = ['fort.10']

        self.db_info['db_name'] = os.path.join(self.study_path, 'data.db')
        self.db_info['db_type'] = 'sql'
        #Default definition of the database tables
        self.tables['templates'] = collections.OrderedDict()
        self.tables['env'] = collections.OrderedDict()
        self.tables['preprocess_wu'] = collections.OrderedDict([
                ('wu_id', 'int'),
                ('job_name', 'text'),
                ('input_file', 'blob'),
                ('batch_name', 'text'),
                ('unique_id', 'text'),
                ('status', 'text'),
                ('task_id', 'int'),
                ('mtime', 'float')])
        self.table_keys['preprocess_wu'] = {
                'primary': ['wu_id'],
                'foreign': {},
                }
        self.tables['preprocess_task'] = collections.OrderedDict([
                ('task_id', 'int'),
                ('wu_id', 'int'),
                ('task_name', 'text'),
                ('madx_in' , 'blob'),
                ('madx_stdout', 'blob'),
                ('job_stdout', 'blob'),
                ('job_stderr', 'blob'),
                ('job_stdlog', 'blob'),
                ('count', 'int'),
                ('status', 'text'),
                ('mtime', 'float')])
        self.table_keys['preprocess_task'] = {
                'primary': ['task_id'],
                'foreign': {'preprocess_wu': [['wu_id'], ['wu_id']]},
                }
        self.tables['oneturn_sixtrack_wu'] = collections.OrderedDict()
        self.tables['preprocess_optics'] = {
                'task_id': 'int',
                'wu_id': 'int'}
        self.tables['oneturn_sixtrack_result'] = collections.OrderedDict([
                ('task_id', 'int'),
                ('wu_id', 'int'),
                ('betax', 'float'),
                ('betax2', 'float'),
                ('betay', 'float'),
                ('betay2', 'float'),
                ('tunex', 'float'),
                ('tuney', 'float'),
                ('chromx', 'float'),
                ('chromy', 'float'),
                ('x', 'float'),
                ('xp', 'float'),
                ('y', 'float'),
                ('yp', 'float'),
                ('z', 'float'),
                ('zp', 'float'),
                ('chromx_s', 'float'),
                ('chromy_s', 'float'),
                ('chrom_eps', 'float'),
                ('tunex1', 'float'),
                ('tuney1', 'float'),
                ('tunex2', 'float'),
                ('tuney2', 'float'),
                ('mtim', 'float')])
        self.tables['sixtrack_wu']=collections.OrderedDict([
                ('wu_id', 'int'),
                ('preprocess_id', 'int'),
                ('job_name', 'text'),
                ('input_file', 'blob'),
                ('batch_name', 'text'),
                ('unique_id', 'text'),
                ('status', 'text'),
                ('task_id', 'int'),
                ('mtime', 'float')])
        self.table_keys['sixtrack_wu'] = {
                'primary': ['wu_id'],
                'foreign': {'preprocess_wu': [['preprocess_id'], ['wu_id']]},
                }
        self.tables['sixtrack_task'] = collections.OrderedDict([
                ('task_id', 'int'),
                ('wu_id', 'int'),
                ('task_name', 'text'),
                ('fort3', 'blob'),
                ('job_stdout', 'blob'),
                ('job_stderr', 'blob'),
                ('job_stdlog', 'blob'),
                ('count', 'int'),
                ('status', 'text'),
                ('mtime', 'float')])
        self.table_keys['sixtrack_task'] = {
                'primary': ['task_id'],
                'foreign': {'sixtrack_wu': [['wu_id'], ['wu_id']]},
                }
        self.tables['six_results'] = collections.OrderedDict([
                ('six_input_id', 'int'),
                ('row_num', 'int'),
                ('turn_max', 'int'),
                ('sflag', 'int'),
                ('qx', 'float'),
                ('qy', 'float'),
                ('betx', 'float'),
                ('bety', 'float'),
                ('sigx1', 'float'),
                ('sigy1', 'float'),
                ('deltap', 'float'),
                ('dist', 'float'),
                ('distp', 'float'),
                ('qx_det', 'float'),
                ('qx_spread', 'float'),
                ('qy_det', 'float'),
                ('qy_spread', 'float'),
                ('resxfact', 'float'),
                ('resyfact', 'float'),
                ('resorder', 'int'),
                ('smearx', 'float'),
                ('smeary', 'float'),
                ('smeart', 'float'),
                ('sturns1', 'int'),
                ('sturns2', 'int'),
                ('sseed', 'float'),
                ('qs', 'float'),
                ('sigx2', 'float'),
                ('sigy2', 'float'),
                ('sigxmin', 'float'),
                ('sigxavg', 'float'),
                ('sigxmax', 'float'),
                ('sigymin', 'float'),
                ('sigyavg', 'float'),
                ('sigymax', 'float'),
                ('sigxminld', 'float'),
                ('sigxavgld', 'float'),
                ('sigxmaxld', 'float'),
                ('sigyminld', 'float'),
                ('sigyavgld', 'float'),
                ('sigymaxld', 'float'),
                ('sigxminnld', 'float'),
                ('sigxavgnld', 'float'),
                ('sigxmaxnld', 'float'),
                ('sigyminnld', 'float'),
                ('sigyavgnld', 'float'),
                ('sigymaxnld', 'float'),
                ('emitx', 'float'),
                ('emity', 'float'),
                ('betx2', 'float'),
                ('bety2', 'float'),
                ('qpx', 'float'),
                ('qpy', 'float'),
                ('version', 'float'),
                ('cx', 'float'),
                ('cy', 'float'),
                ('csigma', 'float'),
                ('xp', 'float'),
                ('yp', 'float'),
                ('delta', 'float'),
                ('dnms', 'float'),
                ('trttime', 'float'),
                ('mtime','float')])
        self.table_keys['six_results'] = {
                'primary': ['six_input_id', 'row_num'],
                'foreign': {'sixtrack_task': [['six_input_id'], ['task_id']]},
                }
        self.db_settings = {
                'synchronous': 'off',
                'foreign_keys': 'on',
                'journal_mode': 'memory',
                'auto_vacuum': 'full',
                'temp_store': 'memory',
                'count_changes': 'off'}

        self.tables['boinc_vars'] = collections.OrderedDict()
        self.boinc_vars['workunitName'] = 'sixdesk'
        self.boinc_vars['fpopsEstimate'] = 30*2*10e5/2*10e6*6
        self.boinc_vars['fpopsBound'] = self.boinc_vars['fpopsEstimate']*1000
        self.boinc_vars['memBound'] = 100000000
        self.boinc_vars['diskBound'] = 200000000
        self.boinc_vars['delayBound'] = 2400000
        self.boinc_vars['redundancy'] = 2
        self.boinc_vars['copies'] = 2
        self.boinc_vars['errors'] = 5
        self.boinc_vars['numIssues'] = 5
        self.boinc_vars['resultsWithoutConcensus'] = 3
        self.boinc_vars['appName'] = 'sixtrack'
        self.boinc_vars['appVer'] = 50205

    def _structure(self):
        '''Structure the workspace of this study.
        Prepare the input and output folders.
        Copy the required template files.
        Initialize the database.'''
        temp = self.paths["templates"]
        if not os.path.isdir(temp) or not os.listdir(temp):
            if not os.path.exists(temp):
                os.makedirs(temp)
            tem_path = os.path.join(utils.PYSIXDESK_ABSPATH, 'templates')
            if os.path.isdir(tem_path) and os.listdir(tem_path):
                for item in os.listdir(tem_path):
                    s = os.path.join(tem_path, item)
                    d = os.path.join(temp, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                content = "Copy templates from default source templates folder!"
                utils.message('Message', content, self.mes_level, self.log_file)
            else:
                content = "The default source templates folder %s is inavlid!"%tem_path
                utils.message('Error', content, self.mes_level, self.log_file)
                sys.exit(1)

        if not os.path.isdir(self.paths["preprocess_in"]):
            os.makedirs(self.paths["preprocess_in"])
        if not os.path.isdir(self.paths["preprocess_out"]):
            os.makedirs(self.paths["preprocess_out"])
        if not os.path.isdir(self.paths["sixtrack_in"]):
            os.makedirs(self.paths["sixtrack_in"])
        if not os.path.isdir(self.paths["sixtrack_out"]):
            os.makedirs(self.paths["sixtrack_out"])
        if not os.path.isdir(self.paths["gather"]):
            os.makedirs(self.paths["gather"])

        #Initialize the database
        #dbname = os.path.join(self.study_path, self.dbname)
        self.db = SixDB(self.db_info, self.db_settings, True)

    def customize(self):
        '''Update the column names of database tables  and initialize the
        submission module after the user define the necessary variables.
        '''
        for key in self.madx_params.keys():
            self.tables['preprocess_wu'][key] = 'INT'
        for key in self.madx_output.values():
            self.tables['preprocess_task'][key] = 'BLOB'

        for key in self.oneturn_sixtrack_params.keys():
            self.tables['oneturn_sixtrack_wu'][key] = 'INT'

        for key in self.sixtrack_params.keys():
            self.tables['sixtrack_wu'][key] = 'INT'
        for key in self.sixtrack_output:
            self.tables['sixtrack_task'][key] = 'BLOB'

        for key in self.madx_input.keys():
            self.tables['templates'][key] = 'BLOB'
        for key in self.oneturn_sixtrack_input['temp']:
            self.tables['templates'][key] = 'BLOB'
        for key in self.sixtrack_input['temp']:
            self.tables['templates'][key] = 'BLOB'

        for key in self.paths.keys():
            self.tables['env'][key] = 'TEXT'
        for key in self.env.keys():
            self.tables['env'][key] = 'INT'

        for key in self.boinc_vars.keys():
            self.tables['boinc_vars'][key] = 'TEXT'
        #create the database tables if not exist
        if not self.db.fetch_tables():
            self.db.create_tables(self.tables, self.table_keys)

        #Initialize the submission object
        cluster_module = self.cluster_module
        classname = self.cluster_name
        if cluster_module is None:
            cluster_module = os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'submission.py')
        if os.path.isfile(cluster_module):
            module_name = os.path.abspath(cluster_module)
            module_name = module_name.replace('.py', '')
            try:
                mod = SourceFileLoader(module_name, cluster_module).load_module()
                cls = getattr(mod, classname)
                #pass temp path to submission class
                self.submission = cls(self.mes_level, self.log_file, self.paths['templates'])
            except:
                content = traceback.print_exc()
                utils.message('Error', content, self.mes_level, self.log_file)
                content = "Failed to initialize submission module!"
                utils.message('Error', content, self.mes_level, self.log_file)
                sys.exit(1)
        else:
            content = "The submission module %s doesn't exist!"%cluster_module
            utils.message('Error', content, self.mes_level, self.log_file)
            sys.exit(1)


    def update_db(self):
        '''Update the database whith the user-defined parameters'''
        temp = self.paths["templates"]
        cont = os.listdir(temp)
        require = []
        require += self.oneturn_sixtrack_input["temp"]
        require.append(self.madx_input["mask_file"])
        for re in require:
            if re not in cont:
                content = "The required file %s isn't found in %s!"%(re, temp)
                utils.message('Error', content, self.mes_level, self.log_file)
                return
        outputs = self.db.select('templates', self.tables['templates'].keys())
        if not outputs:
            tab = {}
            for key,value in self.madx_input.items():
                value = os.path.join(self.study_path, value)
                tab[key] = utils.evlt(utils.compress_buf, [value])
            for key in self.oneturn_sixtrack_input['temp']:
                value = os.path.join(self.study_path, key)
                tab[key] = utils.evlt(utils.compress_buf, [value])
            for key in self.sixtrack_input['temp']:
                value = os.path.join(self.study_path, key)
                tab[key] = utils.evlt(utils.compress_buf, [value])
            self.db.insert('templates', tab)
        outputs = self.db.select('env', self.paths.keys())
        envs = {}
        envs.update(self.paths)
        envs.update(self.env)
        if not outputs:
            self.db.insert('env', envs)
        outputs = self.db.select('boinc_vars', self.boinc_vars.keys())
        if not outputs:
            self.db.insert('boinc_vars', self.boinc_vars)

        self.config.clear()
        self.config['madx'] = {}
        madx_sec = self.config['madx']
        self.config['mask'] = {}
        mask_sec = self.config['mask']
        self.config['sixtrack'] = {}
        six_sec = self.config['sixtrack']
        madx_sec['source_path'] = self.paths['templates']
        madx_sec['madx_exe'] = self.paths['madx_exe']
        madx_sec['mask_file'] = self.madx_input["mask_file"]
        inp = self.madx_output
        madx_sec['output_files'] = utils.evlt(utils.encode_strings, [inp])
        six_sec['source_path'] = self.paths['templates']
        six_sec['sixtrack_exe'] = self.paths['sixtrack_exe']
        inp = self.oneturn_sixtrack_input['temp']
        six_sec['temp_files'] = utils.evlt(utils.encode_strings, [inp])
        inp = self.oneturn_sixtrack_input['input']
        six_sec['input_files'] = utils.evlt(utils.encode_strings, [inp])
        inp = self.oneturn_sixtrack_output
        six_sec['output_files'] = utils.evlt(utils.encode_strings, [inp])
        self.config['fort3'] = self.oneturn_sixtrack_params

        keys = list(self.madx_params.keys())
        values = []
        for key in keys:
            val = self.madx_params[key]
            if not isinstance(val, collections.Iterable) or isinstance(val, str):
                val = [val]#wrap with list for a single element
            values.append(val)

        check_params = self.db.select('preprocess_wu', keys)
        check_jobs = self.db.select('preprocess_wu', ['wu_id','job_name','status'])

        wu_id = len(check_params)
        for element in itertools.product(*values):
            madx_table = collections.OrderedDict()
            if element in check_params:
                i = check_params.index(element)
                name = check_jobs[i][1]
                content = "The job %s is already in the database!"%name
                utils.message('Warning', content, self.mes_level, self.log_file)
                continue
            for i in range(len(element)):
                ky = keys[i]
                vl = element[i]
                mask_sec[ky] = str(vl)
                madx_table[ky] = vl
            prefix = self.madx_input['mask_file'].split('.')[0]
            job_name = self.name_conven(prefix, keys, element, '')
            madx_input = self.paths['preprocess_in']
            wu_id +=1
            madx_table['wu_id'] = wu_id
            n = str(wu_id)
            madx_sec['dest_path'] = os.path.join(self.paths['preprocess_out'], n)
            six_sec['dest_path'] = os.path.join(self.paths['preprocess_out'], n)
            f_out = io.StringIO()
            self.config.write(f_out)
            out = f_out.getvalue()
            madx_table['input_file'] = utils.evlt(utils.compress_buf, [out,'str'])
            madx_table['status'] = 'incomplete'
            madx_table['job_name'] = job_name
            madx_table['mtime'] = time.time()
            self.db.insert('preprocess_wu', madx_table)
            content = 'Store preprocess job %s into database!'%job_name
            utils.message('Message', content, self.mes_level, self.log_file)

        #prepare sixtrack paramters in database
        self.config.clear()
        self.config['sixtrack'] = {}
        six_sec = self.config['sixtrack']
        self.config['fort3'] = {}
        fort3_sec = self.config['fort3']
        six_sec['source_path'] = self.paths['templates']
        six_sec['sixtrack_exe'] = self.paths['sixtrack_exe']
        inp = self.sixtrack_input['input']
        six_sec['input_files'] = utils.evlt(utils.encode_strings, [inp])
        six_sec['boinc_dir'] = self.paths['boinc_spool']
        inp = self.sixtrack_input['temp']
        six_sec['temp_files'] = utils.evlt(utils.encode_strings, [inp])
        inp = self.sixtrack_output
        six_sec['output_files'] = utils.evlt(utils.encode_strings, [inp])

        madx_keys = list(self.madx_params.keys())
        madx_vals = self.db.select('preprocess_wu', ['wu_id']+madx_keys)
        if not madx_vals:
            content = "The preprocess_wu table is empty!"
            utils.message('Warning', content, self.mes_level, self.log_file)
            return
        madx_vals = list(zip(*madx_vals))
        madx_ids = list(madx_vals[0])
        madx_params = madx_vals[1:]
        keys = list(self.sixtrack_params.keys())
        values = []
        for key in keys:
            val = self.sixtrack_params[key]
            if not isinstance(val, collections.Iterable) or isinstance(val, str):
                val = [val]#wrap with list for a single element
            values.append(val)

        keys.append('preprocess_id')
        values.append(madx_ids)
        outputs = self.db.select('sixtrack_wu', keys)
        namevsid = self.db.select('sixtrack_wu', ['wu_id', 'job_name'])
        wu_id = len(namevsid)
        for element in itertools.product(*values):
            job_table = collections.OrderedDict()
            a=[]
            for i in element:
                if isinstance(i, collections.Iterable):
                    i = str(i)
                a.append(i)
            element = tuple(a)
            if element in outputs:
                i = outputs.index(element)
                nm = namevsid[i][1]
                content = "The sixtrack job %s is already in the database!"%nm
                utils.message('Warning', content, self.mes_level, self.log_file)
                continue
            for i in range(len(element)-1):
                ky = keys[i]
                vl = element[i]
                fort3_sec[ky] = str(vl)
                if isinstance(vl, collections.Iterable):
                    vl = str(vl)
                job_table[ky] = vl
            vl = element[len(element)-1]#the last one is madx_id(wu_id)
            j = madx_ids.index(vl)
            for k in range(len(madx_params)):
                ky = madx_keys[k]
                vl = madx_params[k][j]
                fort3_sec[ky] = str(vl)
            cols = list(self.sixtrack_input['input'].values())
            job_table['preprocess_id'] = j + 1 #in db id begin from 1
            wu_id += 1
            job_table['wu_id'] = wu_id
            job_name = 'sixtrack_job_%i_%i'%(j+1, wu_id)
            job_table['job_name'] = job_name
            dest_path = os.path.join(self.paths['sixtrack_out'], str(wu_id))
            six_sec['dest_path'] = dest_path
            self.config['boinc'] = self.boinc_vars
            f_out = io.StringIO()
            self.config.write(f_out)
            out = f_out.getvalue()
            job_table['input_file'] = utils.evlt(utils.compress_buf, [out,'str'])
            job_table['status'] = 'incomplete'
            job_table['mtime'] = time.time()
            self.db.insert('sixtrack_wu', job_table)
            content = 'Store sixtrack job %s into database!'%job_name
            utils.message('Message', content, self.mes_level, self.log_file)

    def info(self, job=2, where=None):
        '''Print the status information of this study.
        job=
        0: print madx, oneturn sixtrack job
        1: print sixtrack job
        2: print madx, oneturn sixtrack and sixtrack jobs
        wehre: the filter condition for database query, e.g. "status='complete'" '''
        loc = self.study_path
        conts = os.listdir(loc)
        if self.dbname not in conts:
            content = "This study directory is empty!"
            utils.message('Warning', content, self.mes_level, self.log_file)
        else:
            query= ['wu_id', 'job_name', 'status', 'unique_id']
            if job==0 or job==2:
                wus = self.db.select('preprocess_wu', query, where)
                print('madx and one turn sixtrack jobs:')
                print(query)
                for i in wus:
                    print(i)
            if job==1 or job==2:
                six = self.db.select('sixtrack_wu', query, where)
                print('Sixtrack jobs:')
                print(query)
                for j in six:
                    print(j)

    def submit(self, typ, trials=5, *args, **kwargs):
        '''Sumbit the preporcess or sixtrack jobs to htctondor.
        @type(0 or 1) The job type, 0 is preprocess job, 1 is sixtrack job
        @trials The maximum number of trials of submission'''
        if typ == 0:
            input_path = self.paths['preprocess_in']
            output_path = self.paths['preprocess_out']
            exe = os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'preprocess.py')
            jobname = 'preprocess'
            table_name = 'preprocess_wu'
        elif typ == 1:
            input_path = self.paths['sixtrack_in']
            output_path = self.paths['sixtrack_out']
            exe = os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'sixtrack.py')
            jobname = 'sixtrack'
            table_name = 'sixtrack_wu'
        else:
            content = "Unknow job type %s"%typ
            utils.message('Error', content, self.mes_level, self.log_file)
            return

        batch_name = os.path.join(self.study_path, jobname)
        where = "batch_name like '%s_%%'"%batch_name
        que_out = self.db.select(table_name, 'batch_name', where, DISTINCT=True)
        ibatch = len(que_out)
        ibatch += 1
        batch_name = batch_name+'_'+str(ibatch)
        status, out = self.submission.submit(input_path, batch_name,
                trials, *args, *kwargs)
        if status:
            content = "Submit %s job successfully!"%jobname
            utils.message('Message', content, self.mes_level, self.log_file)
            table = {}
            table['status'] = 'submitted'
            for ky, vl in out.items():
                where = 'wu_id=%s'%ky
                table['unique_id'] = vl
                table['batch_name'] = batch_name
                self.db.update(table_name, table, where)
        else:
            content = "Failed to submit %s job!"%jobname
            utils.message('Warning', content, self.mes_level, self.log_file)

    def collect_result(self, typ, trials=5, platform='local', clean='False'):
        '''Collect the results of preprocess or  sixtrack jobs'''
        self.config.clear()
        self.config['info'] = {}
        info_sec = self.config['info']
        self.config['db_setting'] = self.db_settings
        self.config['db_info'] = self.db_info
        info_sec['mes_level'] = str(self.mes_level)
        if self.log_file is None:
            info_sec['log_file'] = ''
        else:
            info_sec['log_file'] = self.log_file
        cluster_module = self.cluster_module
        if cluster_module is None:
            cluster_module = os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'submission.py')
        info_sec['cluster_module'] = str(cluster_module)
        info_sec['cluster_name'] = self.cluster_name
        info_sec['clean'] = clean
        if typ == 0:
            self.config['oneturn'] = self.tables['oneturn_sixtrack_result']
            info_sec['path'] = self.paths['preprocess_out']
            info_sec['outs'] = utils.evlt(utils.encode_strings, [self.madx_output])
            job_name = 'collect preprocess reslut'
            in_name = 'preprocess.ini'
            task_input = os.path.join(self.paths['gather'], str(typ), in_name)
        elif typ == 1:
            self.config['f10'] = self.tables['six_results']
            info_sec['path'] = self.paths['sixtrack_out']
            info_sec['outs'] = utils.evlt(utils.encode_strings, [self.sixtrack_output])
            job_name = 'collect sixtrack reslut'
            in_name = 'sixtrack.ini'
            task_input = os.path.join(self.paths['gather'], str(typ), in_name)
        else:
            content = "Unkown job type %s"%typ
            utils.message('Error', content, self.mes_level, self.log_file)

        in_path = os.path.join(self.paths['gather'], str(typ))
        out_path = in_path
        if not os.path.isdir(in_path):
            os.makedirs(in_path)
        with open(task_input, 'w') as f_out:
            self.config.write(f_out)
        if platform is 'local':
            gather.run(typ, task_input)
        elif platform is 'htcondor':
            tran_input =[]
            tran_input.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'utils.py'))
            tran_input.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'pysixdb.py'))
            tran_input.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'dbadaptor.py'))
            tran_input.append(task_input)
            exe = os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'gather.py')
            wu_ids = [typ]
            self.submission.prepare(wu_ids, tran_input, exe, in_name, in_path,
                    out_path)
            self.submission.submit(in_path, job_name, trials)

    def prepare_sixtrack_input(self, boinc=False, *args, **kwargs):
        '''Prepare the input files for sixtrack job'''
        where = "status='complete'"
        preprocess_outs = self.db.select('preprocess_wu', ['wu_id', 'task_id'], where)
        if not preprocess_outs:
            content = "There isn't complete madx job!"
            utils.message('Warning', content, self.mes_level, self.log_file)
            return
        preprocess_outs = list(zip(*preprocess_outs))
        if len(preprocess_outs[0]) == 1:
            where = "status='incomplete' and preprocess_id=%s"%str(preprocess_outs[0][0])
        else:
            where = "status='incomplete' and preprocess_id in %s"%str(preprocess_outs[0])
        outputs = self.db.select('sixtrack_wu', ['wu_id', 'preprocess_id', 'input_file'], where)
        if not outputs:
            content = "There isn't available sixtrack job to submit!"
            utils.message('Warning', content, self.mes_level, self.log_file)
            return
        sub_name = os.path.join(self.paths['sixtrack_in'], 'sub.db')
        sub_main = self.db_info['db_name']
        if os.path.exists(sub_name):
            os.remove(sub_name)#remove the old one
        shutil.copy2(sub_main, sub_name)
        db_info = {}
        db_info['db_name'] = sub_name
        sub_db = SixDB(db_info, self.db_settings)
        sub_db.drop_table('sixtrack_task')
        sub_db.drop_table('result')
        sub_db.drop_table('sixtrack_wu')
        sub_db.drop_table('oneturn_sixtrack_wu')
        sub_db.drop_table('env')
        sub_db.drop_table('templates')
        tables = {'wu_id':'int', 'preprocess_id':'int', 'input_file':'blob',
                'boinc': 'text'}
        sub_db.create_table('sixtrack_wu', tables)
        incom_job = {}
        outputs = list(zip(*outputs))
        wu_ids = []
        pre_ids = []
        input_buf_new = []
        for wu_id, pre_id, buf in zip(outputs[0], outputs[1], outputs[2]):
            in_fil = utils.evlt(utils.decompress_buf, [buf, None, 'buf'])
            self.config.clear()
            self.config.read_string(in_fil)
            paramsdict = self.config['fort3']
            status = self.pre_calc(paramsdict, pre_id)#further calculation
            if status:
                f_out = io.StringIO()
                self.config.write(f_out)
                out = f_out.getvalue()
                buf_new = utils.evlt(utils.compress_buf, [out,'str'])
                input_buf_new.append(buf_new)
                wu_ids.append(wu_id)
                pre_ids.append(pre_id)
        if not wu_ids:
            content = "There isn't available sixtrack job to submit due to "\
                    + "failed furter calculation!"
            utils.message('Error', content, self.mes_level, self.log_file)
            return
        incom_job['wu_id'] = wu_ids
        incom_job['preprocess_id'] = pre_ids
        incom_job['input_file'] = input_buf_new
        incom_job['boinc'] = ['false']*len(wu_ids)
        if boinc:
            incom_job['boinc'] = ['true']*len(wu_ids)
        sub_db.insertm('sixtrack_wu', incom_job)
        wu_ids = sub_db.select('sixtrack_wu', ['wu_id'])
        wu_ids = list(zip(*wu_ids))[0]
        sub_db.close()
        content = "The submitted database %s is ready!"%sub_name
        utils.message('Message', content, self.mes_level, self.log_file)
        tran_input =[]
        tran_input.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'utils.py'))
        tran_input.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'pysixdb.py'))
        tran_input.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'dbadaptor.py'))
        tran_input.append(sub_name)
        in_path = self.paths['sixtrack_in']
        out_path = self.paths['sixtrack_out']
        exe = os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'sixtrack.py')
        self.submission.prepare(wu_ids, tran_input, exe, 'sub.db', in_path,
                    out_path, *args, **kwargs)

    def prepare_preprocess_input(self, *args, **kwargs):
        '''Prepare the input files for madx and one turn sixtrack job'''
        where = "status='incomplete'"
        outputs = self.db.select('preprocess_wu', ['wu_id', 'input_file'], where)
        if not outputs:
            content = "There isn't incomplete preprocess job!"
            utils.message('Warning', content, self.mes_level, self.log_file)
            return
        sub_name = os.path.join(self.paths['preprocess_in'], 'sub.db')
        if os.path.exists(sub_name):
            os.remove(sub_name)#remove the old one
        db_info = {}
        db_info['db_name'] = sub_name
        sub_db = SixDB(db_info, self.db_settings, create=True)
        sub_db.create_table('preprocess_wu', {'wu_id':'int','input_file':'blob'})
        incom_job = {}
        outputs = list(zip(*outputs))
        incom_job['wu_id'] = outputs[0]
        incom_job['input_file'] = outputs[1]
        sub_db.insertm('preprocess_wu', incom_job)
        wu_ids = sub_db.select('preprocess_wu', 'wu_id')
        wu_ids = list(zip(*wu_ids))[0]
        sub_db.close()
        content = "The submitted database %s is ready!"%sub_name
        utils.message('Message', content, self.mes_level, self.log_file)
        trans =[]
        trans.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'utils.py'))
        trans.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'pysixdb.py'))
        trans.append(os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'dbadaptor.py'))
        trans.append(sub_name)
        in_path = self.paths['preprocess_in']
        out_path = self.paths['preprocess_out']
        exe = os.path.join(utils.PYSIXDESK_ABSPATH, 'lib', 'preprocess.py')
        self.submission.prepare(wu_ids, trans, exe, 'sub.db', in_path,
                out_path, *args, **kwargs)

    def pre_calc(self, **args):
        '''Further calculations for the specified parameters'''
        pass

    def name_conven(self, prefix, keys, values, suffix=''):
        '''The convention for naming input file'''
        b = ''
        if len(keys) == len(values):
            a = ['_'.join(map(str, i)) for i in zip(keys, values)]
            b = '_'.join(map(str, a))
        else:
            content = "The input list keys and values must have same length!"
            utils.message('Error', content, self.mes_level, self.log_file)
        mk = prefix + '_' + b + suffix
        return mk

    def __del__(self):
        '''The destructor'''
        self.db.close()
        content = 'Database is closed!'
        utils.message('Message', content, self.mes_level, self.log_file)
