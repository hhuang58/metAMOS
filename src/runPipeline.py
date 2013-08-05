#!python

## $Id$

#########################
## runPipeline.py - main pipeline driver for metAMOS
#########################
##first imports
import os,sys,site
sys.tracebacklimit = 0
shellv = os.environ["SHELL"]
## Setting up paths
INITIAL_SRC   = "%s%ssrc"%(sys.path[0], os.sep)
## Hardcode a k-mer size
DEFAULT_KMER  = 31
## Hardcode a default taxonomic classification level
DEFAULT_TAXA_LEVEL = "class"
sys.path.append(INITIAL_SRC)
import check_install
validate_install = 0
if validate_install:
    rt = check_install.validate_dir(sys.path[0].strip(),sys.path[0]+os.sep+'required_file_list.txt')
    if rt == -1:
        print "MetAMOS not properly installed, please reinstall or contact development team for assistance"
        sys.exit(1)
import utils
ppath = ""
if "PYTHONPATH" not in os.environ:
   os.environ["PYTHONPATH"] = ""
else:
   ppath = os.environ["PYTHONPATH"] 
   os.environ["PYTHONPATH"] = ""
os.environ["PYTHONPATH"]+=utils.INITIAL_UTILS+os.sep+"python"+os.pathsep
os.environ["PYTHONPATH"]+=utils.INITIAL_UTILS+os.sep+"ruffus"+os.pathsep
os.environ["PYTHONPATH"] += utils.INITIAL_UTILS+os.sep+"python"+os.sep+"pysam"+os.pathsep
os.environ["PYTHONPATH"] += utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib"+os.pathsep
os.environ["PYTHONPATH"] += utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib"+os.sep+"python"+os.pathsep
os.environ["PYTHONPATH"] += utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib64"+os.pathsep
os.environ["PYTHONPATH"] += utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib64"+os.sep+"python"+os.pathsep
os.environ["PYTHONPATH"] += ppath + os.pathsep
site.addsitedir(utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib"+os.sep+"python")
site.addsitedir(utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib64"+os.sep+"python")
sys.path.append(utils.INITIAL_UTILS)
sys.path.append(utils.INITIAL_UTILS+os.sep+"python")
sys.path.append(utils.INITIAL_UTILS+os.sep+"ruffus")
sys.path.append(utils.INITIAL_UTILS+os.sep+"python"+os.sep+"pysam")
sys.path.append(utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib"+os.sep+"python")
sys.path.append(utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib64"+os.sep+"python")

#remove imports from pth file, if exists
nf = []
nopsutil = False
nopysam = False
try:
    dir1 = utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib"+os.sep+"python"
    if not os.path.exists(dir1+os.sep+"easy-install.pth"):
        dir1 = utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib64"+os.sep+"python"

    nf = open(dir1+os.sep+"easy-install.pth",'r')
    ndata = []
    for line in nf.xreadlines():
        if "import" in line:
            continue
        ndata.append(line)
    nf.close()
    nfo = open(dir1+os.sep+"easy-install.pth",'w')
    for line in ndata:
        nfo.write(line)
    nfo.close()
except IOError:
    print "ERROR: easy-install.pth file missing, likely means something went wrong with psutil/pysam install. Disabling psutil and pysam.."
    nopsutil = True
    nopysam = True
    #sys.exit(1)

if 'bash' in shellv or utils.cmdExists('export'):
   os.system("export PYTHONPATH=%s:$PYTHONPATH"%(utils.INITIAL_UTILS+os.sep+"python"))
   os.system("export PYTHONPATH=%s:$PYTHONPATH"%(utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib"+os.sep+"python"))
elif utils.cmdExists('setenv'):
   os.system("setenv PYTHONPATH %s:$PYTHONPATH"%(utils.INITIAL_UTILS+os.sep+"python"))
   os.system("setenv PYTHONPATH %s:$PYTHONPATH"%(utils.INITIAL_UTILS+os.sep+"python"+os.sep+"lib"+os.sep+"python"))
else:
   print "Warning: could not set PYTHONPATH. Unknown shell %s, some functionality may not work\n"%(shellv)
## The usual library dependencies
import string
import time
import datetime
import BaseHTTPServer
import getopt
import re
import subprocess
import webbrowser
import multiprocessing
if not nopsutil:
    import psutil
from operator import itemgetter
from ruffus import *
skipsteps = ["FindRepeats"]

## Get start time
t1 = time.time()

def usage():
    print "usage: runPipeline [options] -d projectdir"
    print "   -h = <bool>:   print help [this message]"
    print "   -j = <bool>:   just output all of the programs and citations then exit (default = NO)"
    print "   -v = <bool>:   verbose output? (default = NO)"
    print "   -d = <string>: directory created by initPipeline (REQUIRED)"

    print "\n[options]: [pipeline_opts] [misc_opts]"
    print "\n[pipeline_opts]: options that affect the pipeline execution"

    print "Pipeline consists of the following steps:"
    print "  Preprocess, Assemble, FindORFS, MapReads, Abundance, Annotate,"
    print "  FunctionalAnnotation, Scaffold, Propagate, Classify, Postprocess"

    print "Each of these steps can be referred to by the following options:" 
    print "   -f = <string>: force this step to be run (default = NONE)"
    print "   -s = <string>: start at this step in the pipeline (default = Preprocess)"
    print "   -e = <string>: end at this step in the pipeline (default = Postprocess)"
    print "   -n = <string>: step to skip in pipeline (default=NONE)"

    print "\nFor each step you can fine-tune the execution as follows"
    print "[Preprocess]"
    print "   -t = <bool>:   filter input reads? (default = NO)"
    print "   -q = <bool>:   produce FastQC quality report for reads with quality information (fastq or sff)? (default = NO)"
    print "[Assemble]"
    print "   -a = <string>: genome assembler to use (default = SOAPdenovo)"
    print "   -k = <kmer size>: k-mer size to be used for assembly (default = " + str(DEFAULT_KMER) +  ")"
    print "   -o = <int>>:   min overlap length"
    print "[MapReads]"
    print "   -m = <string>: read mapper to use? (default = bowtie)"
    print "   -i = <bool>:   save bowtie (i)ndex? (default = NO)"
    print "   -b = <bool>:   create library specific per bp coverage of assembled contigs (default = NO)"
    print "[FindORFS]"
    print "   -g = <string>: gene caller to use (default=FragGeneScan)"
    print "   -l = <int>:    min contig length to use for ORF call (default = 300)"
    print "   -x = <int>>:   min contig coverage to use for ORF call (default = 3X)"
    print "[Annotate]"
    print "   -c = <string>: classifier to use for annotation (default = FCP)"
    print "   -u = <bool>:   annotate unassembled reads? (default = NO)"

    print "[Classify]"
    print "   -z = <string>: taxonomic level to categorize at (default = %s)"%(DEFAULT_TAXA_LEVEL)

    print "\n[misc_opts]: Miscellaneous options"
    print "   -r = <bool>:   retain the AMOS bank?  (default = NO)"
    print "   -p = <int>:    number of threads to use (be greedy!) (default=1)"
    print "   -4 = <bool>:   454 data? (default = NO)"    

def updateCounter():
    ##if user says its ok, create MetAMOS counter git repo and update counter each time its run!
    if os.path.exists("%s/config/usage.ok"%(utils.Settings.METAMOS_UTILS)):
        FORMAT = '%Y%m%d%H%M%S'
        filestamp = datetime.datetime.now().strftime(FORMAT)
        #print filestamp, utils.Settings.METAMOS_UTILS
        #"%s/pipeline.run"%(settings.rundir)) 
        os.system("cat %s/pipeline.run > %s/%s.txt"%(utils.Settings.rundir,utils.Settings.rundir,filestamp))
        #print "%s/config/updateftpcounter.sh %s/%s.txt %s.txt"%(utils.Settings.METAMOS_UTILS,utils.Settings.rundir,filestamp,filestamp)
        os.system("%s/config/updateftpcounter.sh %s/%s.txt %s.txt >& ftp.out"%(utils.Settings.METAMOS_UTILS,utils.Settings.rundir,filestamp,filestamp))

def printConfiguration(fileName=None):
    configurationText = []
    configurationText.append("metAMOS configuration summary:\n")
    configurationText.append("Time and Date:\t\t%s\n"%(str(datetime.date.today())))
    configurationText.append("Working directory:\t%s\n"%(utils.Settings.rundir))
    configurationText.append("Prefix:\t\t\t%s\n"%(utils.Settings.PREFIX))
    configurationText.append("K-Mer:\t\t\t%d\n"%(utils.Settings.kmer))
    configurationText.append("Threads:\t\t%d\n"%(utils.Settings.threads)) 
    configurationText.append("Taxonomic level:\t%s\n"%(utils.Settings.taxa_level))
    configurationText.append("Verbose:\t\t%s\n"%(utils.Settings.VERBOSE))
    configurationText.append("Steps to skip:\t\t%s\n"%(", ".join(skipsteps)))
    configurationText.append("Steps to force:\t\t%s\n"%(", ".join(forcesteps)))

    configurationText.append("\n")
    configurationText.append("Step-specific configuration:\n")
    for type in selected_programs.keys():
        configurationText.append("[" + type + "]\n")
        prog = selected_programs[type]

        #If there are multiple assemblers, refer to multiple_assemblers list for program citations
        if prog=="allassemblers" or "multassemblers":
           for assem in multiple_assemblers:
              (progName, citation) = utils.getProgramCitations(settings, assem)
              configurationText.append(progName + "\n")
              try:
                 configurationText.append("\t" + eval("utils.Settings.%s"%(assem.replace("-", "_").upper()))+"\n")
              except AttributeError:
                 configurationText.append("\tUNKNOWN\n")
                 configurationText.append("\t" + citation + "\n\n")
           continue 

        if prog == None or prog == "none":
           configurationText.append("None\n\n")
        else:
           (progName, citation) = utils.getProgramCitations(settings, prog)
           configurationText.append(progName + "\n")
           try:
              configurationText.append("\t" + eval("utils.Settings.%s"%(prog.replace("-", "_").upper()))+"\n")
           except AttributeError:
              configurationText.append("\tUNKNOWN\n")
           configurationText.append("\t" + citation + "\n\n")

    # add step-indepent citations that are always run
    configurationText.append("[other]\n")
    for prog in always_run_programs:
       if prog == None or prog == "none":
          configurationText.append("None\n\n")
       else:
          (progName, citation) = utils.getProgramCitations(settings, prog)
          configurationText.append(progName + "\n")
          try:
             configurationText.append("\t" + eval("utils.Settings.%s"%(prog.upper()))+"\n")
          except AttributeError:
             configurationText.append("\tUNKNOWN\n")
          configurationText.append("\t" + citation + "\n\n")

    if fileName == "" or fileName == None:
        print ''.join(configurationText)
    else:
        conf = open(fileName, 'w')
        conf.write(''.join(configurationText))
        conf.close()

try:
    opts, args = getopt.getopt(sys.argv[1:], "hrjwbd:s:e:o:k:c:a:n:p:qtf:vm:4g:iu1l:x:yz:",\
                                   ["help", \
                                        "retainBank", \
                                        "libspeccov",\
                                        "projectdir",\
                                        "startat",\
                                        "endat", \
                                        "minoverlap",\
                                        "kmersize",\
                                        "classifier",\
                                        "assembler",\
                                        "skipsteps",\
                                        "threads",\
                                        "fastqreport",\
                                        "filter",\
                                        "forcesteps",\
                                        "verbose",\
                                        "mapper",\
                                        "454",\
                                        "genecaller",\
                                        "bowtieindex",\
                                        "unassembledreads",\
                                        "lowmem",\
                                        "minlen",\
                                        "mincov", \
                                        "justprogs", \
                                        "what", \
                                        "lowcpu",\
                                        "taxalevel"])
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)


## always use long names, search will auto-detect abbreviations

supported_programs = {}
supported_genecallers = ["fraggenescan","metagenemark","glimmermg"]
supported_assemblers = ["soapdenovo","newbler","ca","velvet","velvet-sc","metavelvet",\
                            "metaidba","sparseassembler","minimus"]
#To hold multiple assemblers
multiple_assemblers=[]
supported_mappers = ["bowtie","bowtie2"]

if nopysam:
    #need pysam for bowtie2 support
    supported_mappers = ["bowtie"]
supported_abundance = ["metaphyler"]
supported_classifiers = ["fcp","phylosift","phmmer","blast",\
                             "metaphyler", "phymm"]
supported_fannotate = ["blast"]
supported_scaffolders = ["bambus2"]
supported_programs["findorfs"] = supported_genecallers
supported_programs["assemble"] = supported_assemblers
supported_programs["mapreads"] = supported_mappers
supported_programs["abundance"] = supported_abundance
supported_programs["classify"] = supported_classifiers
supported_programs["fannotate"] = supported_fannotate
supported_programs["scaffold"] = supported_scaffolders

supported_taxonomic = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]

selected_programs = {}
selected_programs["assemble"] = "soapdenovo"
selected_programs["findorfs"] = "fraggenescan"
selected_programs["mapreads"] = "bowtie"
selected_programs["abundance"] = "metaphyler"
selected_programs["classify"] = "fcp"
selected_programs["fannotate"] = "blast"
selected_programs["scaffold"] = "bambus2"

always_run_programs = ["krona"]


allsteps = ["Preprocess","Assemble","MapReads","FindORFS","FindRepeats","Abundance","Annotate",\
                "FunctionalAnnotation","Scaffold","FindScaffoldORFS","Propagate","Classify","Postprocess"]

## Need comments here and further down

output = None
reads = None
quals = None
format = None
savebtidx = False
verbose = False
bowtie_mapping = 1
startat = None
endat = None
filter = False
forcesteps = []

run_fastqc = False
runfast = False
retainBank = False

fff = ""
readlen = 75
fqlibs = {}
fqfrags = []
rlibs = []
ctgbpcov = False
min_ctg_len = 300
read_orfs = False
min_ctg_cvg = 3
lowmem= False
annotate_unassembled = False
output_programs = 0
settings = utils.Settings(DEFAULT_KMER, multiprocessing.cpu_count() - 1, "", DEFAULT_TAXA_LEVEL)
nofcpblast = False
bpctgcov = False
for o, a in opts:
    if o in ("-v","--verbose"):
        utils.Settings.VERBOSE = True
    elif o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-i","--indexbowtie"):
        bowtie_mapping = 1
    elif o in ("-y","--lowcpu"):
        nofcpblast = True
    elif o in ("-w","--what"):
        utils.Settings.OUTPUT_ONLY = True
    elif o in ("-j","--justprogs"):
        output_programs = 1
        print "\n======Supported programs and citations (if available)=======\n"
        for type in supported_programs.keys():
            print "[" + type + "]"
            ccnt = 1
            for prog in supported_programs[type]:
                (progName, citation) = utils.getProgramCitations(settings, prog)
                #citation = "NA"
                #try: 
                #    citation = pub_dict[prog]
                #except KeyError:
                #    citation = "NA"
                print "  %d)"%(ccnt)+" "+progName
                print "    "+citation+"\n"
                ccnt +=1
        sys.exit(0)
                
    elif o in ("-u","--unassembledreads"):
        annotate_unassembled = 1
    elif o in ("-x","--xcov"):
        min_ctg_cvg = int(a)
    elif o in ("-l","--lencontigorf"):
        min_ctg_len = int(a)
    elif o in ("-b","--bpctgcov"):
        bpctgcov = True
    elif o in ("-s","--startat"):
        startat = a
        if startat not in allsteps:
            print "cannot start at %s, step does not exist in pipeline"%(startat)
            print allsteps
        skipsteps.extend(allsteps[:allsteps.index(startat)]) 
    elif o in ("-e","--endat"):
        endat = a
        if endat not in allsteps:
            print "cannot end at %s, step does not exist in pipeline"%(endtat)
            print allsteps 
        skipsteps.extend(allsteps[allsteps.index(endat)+1:])
    elif o in ("-o", "--minoverlap"):
        pass
    elif o in ("-k", "--kmersize"):
        utils.Settings.kmer = int(a)
    elif o in ("-4", "--454"):
        fff = "-454"
    elif o in ("-f", "--forcesteps"):
        forcesteps = a.split(",")
    elif o in ("-n", "--skipsteps"):
        skipsteps.extend(a.split(","))
    elif o in ("-p", "--threads"):
        if int(a) > 0:
            utils.Settings.threads = int(a)
    elif o in ("-d", "--projectdir"):
        utils.Settings.rundir = os.path.abspath(a)
        if not os.path.exists(a):
          print "project dir %s does not exist!"%(settings.rundir)
          usage()
          sys.exit(1)
    elif o in ("-q", "--fastqc"):
        run_fastqc = True
    elif o in ("-t", "--filter"):
        filter = True

    elif o in ("-m", "--mapper"):
        selected_programs["mapreads"] = a.lower()
        foundit = False
        for sm in supported_mappers:
            if selected_programs["mapreads"] not in sm:
                continue
            else:
                selected_programs["mapreads"] = sm
                foundit = True
                break
        if not foundit:
            print "!!Sorry, %s is not a supported read alignment method. Using bowtie instead"%(selected_programs["mapreads"])
            selected_programs["mapreads"] = "bowtie"
        #mapper = a
    elif o in ("-r", "--retainBank"):
        retainBank = True
    elif o in ("-c", "--classifier"):
        selected_programs["classify"] = a.lower()
        foundit = False
        for sc in supported_classifiers:
            if selected_programs["classify"] not in sc:
                continue
            else:
                selected_programs["classify"] = sc
                foundit = True
                break
        if sc == "metaphyler":
            #not quite ready for primetime, need krona import script and annots file
            skipsteps.append("Propagate")
            skipsteps.append("Classify")
        if not foundit:
            print "!!Sorry, %s is not a supported classification method. Using FCP instead"%(selected_programs["classify"])
            selected_programs["classify"] = "fcp"
    elif o in ("-z", "--taxalevel"):
        utils.Settings.taxa_level = a.lower()

        if utils.Settings.taxa_level not in supported_taxonomic:
           print "!!Sorry, %s is not a valid taxonomic level. Using class instead"%(utils.Settings.taxa_level)

    elif o in ("-1","--lowmem"):
        lowmem = True
    elif o in ("-a","--assembler"):

        assemblers=a.strip().split(',')
	#If multiple assemblers provided, identify and insert each assembler name into a list
        if len(assemblers)>1:
            selected_programs["assemble"]="multassemblers"
            for assem in assemblers:
                for sa in supported_assemblers:
                    if assem in sa:
                        if assem != "velvet":
                        #some special cases required, velvet would trigger MetaVelvet, not velvet, etc
                            if sa not in multiple_assemblers:
                                multiple_assemblers.append(sa)
                        else:
                            multiple_assemblers.append("velvet")
                        break

                    
            if len(multiple_assemblers)==0:
                print "!!Sorry, no supported assemblers specified. Using SOAPdenovo instead"
                selected_programs["assemble"] = "soapdenovo"
                
            if "metaidba" in multiple_assemblers:
                bowtie_mapping=1

            if len(multiple_assemblers) == 1:
                selected_programs["assemble"]=multiple_assemblers.pop()
           # print multiple_assemblers
           # print selected_programs["assemble"]

	#If only one assembler was provided
        else:
            selected_programs["assemble"] = a.lower()
            if selected_programs["assemble"] == "metaidba":
                bowtie_mapping = 1
            
            foundit = False
            
            for sa in supported_assemblers:
                if selected_programs["assemble"] not in sa:
                    continue
                else:
                    if selected_programs["assemble"] != "velvet":
                        #some special cases required, velvet would trigger MetaVelvet, not velvet, etc
                        selected_programs["assemble"] = sa
                    foundit = True
                    break

            #if the allassembler option selected, insert all supported assemblers into list for pipeline step
            if selected_programs["assemble"] in "allassemblers":
                selected_programs["assemble"]="allassemblers"
                multiple_assemblers=supported_assemblers
                bowtie_mapping=1
                foundit=True
            
            if not foundit:
                print "!!Sorry, %s is not a supported assembler. Using SOAPdenovo instead"%(selected_programs["assemble"])
                selected_programs["assemble"] = "soapdenovo"
        
    elif o in ("-g","--genecaller"):
        selected_programs["findorfs"] = a.lower()
        foundit = False
        for sg in supported_genecallers:
            if selected_programs["findorfs"] not in sg:
                continue
            else:
                selected_programs["findorfs"] = sg
                foundit = True
                break
        if selected_programs["findorfs"] == "metagenemark" and "Darwin" in settings.OSTYPE:
            print "!!Sorry, %s is not a supported gene caller for Mac OSX. Using FragGeneScan instead"%(selected_programs["findorfs"])
            selected_programs["findorfs"] = "fraggenescan"
        if not foundit:
            print "!!Sorry, %s is not a supported gene caller. Using FragGeneScan instead"%(selected_programs["findorfs"])
            selected_programs["findorfs"] = "fraggenescan"

    elif o in ("-f","--fastest"):
        runfast = True
    elif o in ("-b","--savebowtieidx"):
        savebtidx = True
    else:
        assert False, "unhandled option"

if not os.path.exists(settings.rundir) or settings.rundir == "":
    print "project dir %s does not exist!"%(settings.rundir)
    usage()
    sys.exit(1)

print "[Steps to be skipped]: ", skipsteps
#remove started & ok flags in Logs
os.system("rm %s%sLogs%s*.started"%(settings.rundir,os.sep,os.sep))
#parse frag/libs out of pipeline.ini out of rundir
inifile = settings.rundir+os.sep+"pipeline.ini"
inf = open(inifile,'r')
libs = []
readlibs = []
readobjs = []
frgs = []
format = ""
mean = 0
stdev = 0
mmin = 0
mmax = 0
mated = True
interleaved = False
innie = True

# This should be an option somewhere and probably belongs to initPipeline
linkerType = "titanium"
frg = ""
f1 = ""
f2 = ""
currlibno = 0
newlib = ""
usecontigs = False
libadded = False

for line in inf:
    line = line.replace("\n","")
    if "#" in line:
        continue
    elif "asmcontigs:" in line:
        asmc = line.replace("\n","").split("\t")[-1]
        if len(asmc) <= 2:
            continue
        utils.run_process(settings, "cp %s %s/Assemble/out/%s"%(asmc,settings.rundir,\
                          "proba.asm.contig"),"RunPipeline")
        usecontigs = True
        selected_programs["assemble"] = "none"
        bowtie_mapping = 1
    elif "format:" in line:

        if f1 and not libadded:
            nread1 = utils.Read(format,f1,mated,interleaved)
            readobjs.append(nread1)
            nread2 = ""
            nlib = utils.readLib(format,mmin,mmax,nread1,nread2,mated,interleaved,innie,linkerType)
            readlibs.append(nlib)
        libadded = False
        format = line.replace("\n","").split("\t")[-1]
    elif "mated:" in line:
        mated = utils.str2bool(line.replace("\n","").split("\t")[-1])
    elif "interleaved:" in line:
        interleaved = utils.str2bool(line.replace("\n","").split("\t")[-1])
    elif "innie:" in line:
        innie = utils.str2bool(line.replace("\n","").split("\t")[-1])
    elif "linker:" in line:
        linkerType = line.replace("\n","").split("\t")[-1]
    elif "f1:" in line:
        data = line.split("\t")

        fqlibs[data[0]] = data[1]
 
        f1 = "%s/Preprocess/in/%s"%(settings.rundir,data[1].split(",")[0])
        inf = data[1].split(",")
        mean = int(inf[3])
        stdev = int(inf[4])
        mmin = int(inf[1])
        mmax = int(inf[2])
        libs.append(f1)

    elif "f2:" in line:
        data = line.split("\t")

        fqlibs[data[0]] = data[1]
        f2 = "%s/Preprocess/in/%s"%(settings.rundir,data[1].split(",")[0])
        inf = data[1].split(",")
        mean = int(inf[3])
        stdev = int(inf[4])
        mmin = int(inf[1])
        mmax = int(inf[2])
        libs.append(f2)
        
        nread1 = utils.Read(format,f1,mated,interleaved)
        readobjs.append(nread1)
        nread2 = utils.Read(format,f2,mated,interleaved)
        readobjs.append(nread2)
        nlib = utils.readLib(format,mmin,mmax,nread1,nread2,mated,interleaved,\
                             innie,linkerType)
        readlibs.append(nlib)
        libadded = True
    elif "frg" in line:

        data = line.split("\t")
        frg = "%s/Preprocess/in/%s"%(settings.rundir,data[1].split(",")[0])
        mated = False
        f1 = frg
        libs.append(frg)
if f1 and not libadded:
    nread1 = utils.Read(format,f1,mated,interleaved)
    readobjs.append(nread1)
    nread2 = ""
    nlib = utils.readLib(format,mmin,mmax,nread1,nread2,mated,interleaved,innie,\
                         linkerType)
    readlibs.append(nlib)

if len(readlibs) > 1 and selected_programs["assemble"] == "metaidba":
    print "ERROR: meta-IDBA only supports 1 library, please select different assembler or reduce libraries"
    sys.exit(1)

infile = ""

if (format == "fastq" and mated):
    infile = f1
elif (format == "fastq" and not mated):
    infile = frg
elif (format == "fasta" and not mated):
    infile = frg
elif format == "sff":
    if frg == "":
       infile = f1
    else:
       infile = frg

readpaths = []
filtreadpaths = []
for lib in readlibs:
   for read in lib.reads:
      readpaths.append("%s/Preprocess/in/"%(settings.rundir)+read.fname)
      filtreadpaths.append("%s/Preprocess/out/"%(settings.rundir)+read.fname)

if "Preprocess" in forcesteps:
   for path in readpaths:
      utils.run_process(settings, "touch %s"%(path),"RunPipeline")
   os.system("rm %s%sLogs%s*.ok"%(settings.rundir,os.sep,os.sep))
utils.Settings.readpaths = readpaths

asmfiles = []

for lib in readlibs:
    if "MapReads" in forcesteps:
        utils.run_process(settings, \
           "touch %s/Assemble/out/%s.asm.contig"%(settings.rundir,settings.PREFIX),\
           "RunPipeline")
    if "Assemble" in forcesteps:
        utils.run_process(settings, \
           "touch %s/Preprocess/out/lib%d.seq"%(settings.rundir,lib.id),\
           "RunPipeline")
    asmfiles.append("%s/Preprocess/out/lib%d.seq"%(settings.rundir,lib.id))


utils.Settings.asmfiles = asmfiles

if "Propagate" in forcesteps:
    utils.run_process(settings, "rm %s/Logs/propagate.ok"%(settings.rundir), "RunPipeline")
    utils.run_process(settings, "touch %s/Annotate/out/%s.annots"%(settings.rundir, settings.PREFIX),\
                      "RunPipeline")

if "FindScaffoldORFS" in forcesteps:
    utils.run_process(settings, \
          "touch %s/Scaffold/out/%s.linearize.scaffolds.final"%(settings.rundir,settings.PREFIX),\
          "RunPipeline")

if "Scaffold" in forcesteps:
    utils.run_process(settings, \
          "rm %s/Scaffold/out/%s.linearize.scaffolds.final"%(settings.rundir,settings.PREFIX),\
          "RunPipeline")

if "Abundance" in forcesteps:
   utils.run_process(settings, \
          "touch %s/FindORFS/out/%s.faa"%(settings.rundir,settings.PREFIX),\
          "RunPipeline")
   utils.run_process(settings, \
          "rm %s/Abundance/out/%s.taxprof.pct.txt"%(settings.rundir,settings.PREFIX),\
          "RunPipeline")

if "Annotate" in forcesteps:
   utils.run_process(settings, \
          "rm %s/Annotate/out/%s.hits"%(settings.rundir,settings.PREFIX),"RunPipeline")

if "FINDORFS" in forcesteps or "findorfs" in forcesteps or "FindORFS" in forcesteps:
   utils.run_process(settings, \
          "rm %s/FindORFS/out/%s.faa"%(settings.rundir,settings.PREFIX),"RunPipeline")
   utils.run_process(settings, \
          "rm %s/FindORFS/out/%s.fna"%(settings.rundir,settings.PREFIX),"RunPipeline")
   utils.run_process(settings, \
          "touch %s/Assemble/out/%s.asm.contig"%(settings.rundir,settings.PREFIX),\
          "RunPipeline")

if "Assemble" not in skipsteps and "Assemble" in forcesteps:
    utils.run_process(settings, \
          "rm %s/Logs/assemble.ok"%(settings.rundir),\
          "RunPipeline")

if __name__ == "__main__":
    print "Starting metAMOS pipeline"
    if settings.threads < 1:
        settings.threads = 1
    settings = utils.initConfig(settings.kmer, settings.threads, settings.rundir, settings.taxa_level, settings.VERBOSE, settings.OUTPUT_ONLY)
    # add krona to system path
    currPath = os.environ["PATH"]
    if utils.Settings.KRONA not in currPath:
       os.environ["PATH"]="%s:%s"%(utils.Settings.KRONA, currPath)

    # check for memory/cpu
    if not nopsutil and lowmem == False:
        cacheusage=0
        if 'linux' in utils.Settings.OSTYPE.lower():
            cacheusage = psutil.cached_phymem()
        memusage =  `psutil.phymem_usage()`.split(",")
        freemem = long(memusage[2].split("free=")[-1])+long(cacheusage)
        percentfree = float(memusage[3].split("percent=")[-1].split(")")[0])
        avram = (freemem/1000000000)
        print "[Available RAM: %d GB]"%(avram)
        lowmem= False
        nofcpblast = False
        if avram <= 32:
            print utils.WARNING_YELLOW+"\tThere is *%d GB of RAM currently available on this machine, suggested minimum of 32 GB"%(avram)+utils.ENDC
            print utils.WARNING_YELLOW+"\t*Enabling low MEM mode, might slow down some steps in pipeline"+utils.ENDC
            print utils.WARNING_YELLOW+"\t*If more RAM is available than what is listed above, please close down other programs and restart runPipeline"+utils.ENDC
            lowmem= True
        else:
            print utils.OK_GREEN+"\t*ok"+utils.ENDC
        numcpus = psutil.NUM_CPUS
        print "[Available CPUs: %d]"%(numcpus)
        if numcpus < 8:
            print utils.WARNING_YELLOW+"\t*Only %d CPU cores available, some modules might take awhile to complete"%(numcpus)+utils.ENDC
            print utils.WARNING_YELLOW+"\t*Disabling all BLAST (where possible)"+utils.ENDC
            nofcpblast = True
            skipsteps.append("FunctionalAnnotation")
        else:
            print utils.OK_GREEN+"\t*ok"+utils.ENDC

    import preprocess
    import assemble
    import mapreads
    import findorfs
    import findreps
    import abundance
    import annotate
    import fannotate
    import scaffold
    import findscforfs
    import propagate
    import classify
    import postprocess

    import shutil

    # initialize submodules
    preprocess.init(readlibs, skipsteps, selected_programs["assemble"], run_fastqc,filter)
    assemble.init(readlibs, skipsteps, selected_programs["assemble"], usecontigs)
    mapreads.init(readlibs, skipsteps, selected_programs["assemble"], selected_programs["mapreads"], savebtidx,ctgbpcov,lowmem)
    findorfs.init(readlibs, skipsteps, selected_programs["assemble"], selected_programs["findorfs"], min_ctg_len, min_ctg_cvg,read_orfs)
    findreps.init(readlibs, skipsteps)
    annotate.init(readlibs, skipsteps, selected_programs["classify"], nofcpblast, annotate_unassembled)
    fannotate.init(skipsteps)
    abundance.init(readlibs, skipsteps, forcesteps, selected_programs["classify"])
    scaffold.init(readlibs, skipsteps, retainBank, selected_programs["assemble"])
    findscforfs.init(readlibs, skipsteps, selected_programs["findorfs"])
    propagate.init(readlibs, skipsteps, selected_programs["classify"])
    classify.init(readlibs, skipsteps, selected_programs["classify"])
    postprocess.init(readlibs, skipsteps, selected_programs["classify"])

    try:
       dlist = []
       pipeline_printout(sys.stdout,[preprocess.Preprocess,assemble.Assemble, \
                         mapreads.MapReads, \
                         findorfs.FindORFS, findreps.FindRepeats, annotate.Annotate, \
                         abundance.Abundance, fannotate.FunctionalAnnotation, scaffold.Scaffold, \
                         findscforfs.FindScaffoldORFS, propagate.Propagate, \
                         classify.Classify, postprocess.Postprocess], verbose=1)

       if not utils.getFromPath("dot", "Graphviz") == "":
          pipeline_printout_graph (   'flowchart.svg',
                               'svg',
                               [postprocess.Postprocess],
                               no_key_legend = True)

       printConfiguration()
       printConfiguration("%s/pipeline.run"%(settings.rundir))
       updateCounter()

       if(selected_programs["assemble"]!="allassemblers" and selected_programs["assemble"]!="multassemblers"):
          pipeline_run([preprocess.Preprocess, assemble.Assemble,findorfs.FindORFS, \
                       mapreads.MapReads, \
                       findreps.FindRepeats, annotate.Annotate, abundance.Abundance, \
                       fannotate.FunctionalAnnotation, scaffold.Scaffold, findscforfs.FindScaffoldORFS, \
                       propagate.Propagate, classify.Classify, postprocess.Postprocess],\
                       verbose = 2)
       else:
          #Modified pipeline to run multiple assemblers
          pipeline_run([preprocess.Preprocess],\
                       verbose = 2)
          assemblerScores={}
          bestAssembler=""
          bestScore=0
          mean=0
          stdev=0
          filereads=""
          filereads1=""
          filereads2=""
          lib=readlibs[0]
          mean=int(lib.mean)
          stdev=int(lib.stdev)

          #Calc_prob setup for interleaved reads
          if lib.interleaved:
              for libs in readlibs:
                  filereads1=filereads1+"%s/Preprocess/out/lib%s.1.fastq"%(settings.rundir,libs.id)
                  filereads2=filereads2+"%s/Preprocess/out/lib%s.2.fastq"%(settings.rundir,libs.id)
                  if libs.id<len(readlibs):
                      filereads1=filereads1+","
                      filereads2=filereads2+","

              filereads="-1 %s -2 %s -m %s -t %s -I %s -X %s "%(filereads1,filereads2,str(mean),str(stdev),str(mean-5*stdev),str(mean+5*stdev))
          #Calc_prob setup for unpaired reads
          elif lib.f2==None:
              for libs in readlibs:
                  filereads1=filereads1+lib.f1.path
                  if libs.id<len(readlibs):
                      filereads1=filereads1+","

              filereads="-i%s -m %s t %s -I %s -X %s "%(filereads1,str(mean),str(stdev),str(mean-5*stdev),str(mean+5*stdev))
          #Calc_prob setup for paired reads
          else:
              for libs in readlibs:
                  filereads1=filereads1+lib.f1.path
                  filereads2=filereads2+lib.f2.path
                  if libs.id<len(readlibs):
                      filereads1=filereads1+","
                      filereads2=filereads2+","

              filereads=="-1 %s -2 %s -m %s -t %s -I %s -X %s "%(filereads1,filereads2,str(mean),str(stdev),str(mean-5*stdev),str(mean+5*stdev))
          #If coverage file exists, include it in the command string for calc.py
          if bpctgcov:
              filereads= filereads+"-n %s/Assemble/out/%s.contig.cvg "%(settings.rundir,settings.PREFIX)
              
          for assembler in multiple_assemblers:
              
              open("%s/Preprocess/out/preprocess.success"%(settings.rundir), "w").close()
              assemble.init(readlibs, skipsteps, assembler, usecontigs)
              if assembler=="minimus":
                  assemble.init(readlibs, skipsteps, "amos", usecontigs)#For some reason, minimus is referred to as "amos" in Assemble.py
                  
              if bpctgcov:
                  pipeline_run([assemble.Assemble,mapreads.MapReads],\
                           verbose = 2)
              else:
                  pipeline_run([assemble.Assemble],\
                           verbose = 2)
              command= "python ../LAP/aligner/calc_prob.py -a %s/Assemble/out/%s.asm.contig %s > %s/Assemble/out/outputScore.prob"%(settings.rundir,settings.PREFIX,filereads,settings.rundir)
              #print command
              os.system(command)
              os.system("python ../LAP/aligner/sum_prob.py -i %s/Assemble/out/outputScore.prob > %s/Assemble/out/totalScore.txt"%(settings.rundir,settings.rundir))

              scoreFile=open("%s/Assemble/out/totalScore.txt"%(settings.rundir),"r")
              score=eval(scoreFile.read().split()[0])
              scoreFile.close()
              #print score
              if bestAssembler=="":
                  bestAssembler=assembler
                  bestScore=score
              if score>bestScore:
                  bestAssembler=assembler
                  bestScore=score
              assemblerScores[assembler]=score

              #Move best results back to pipeline for readmapping/annoation steps
              shutil.move("%s/Assemble/out"%(settings.rundir),"%s/Assemble/temp%s/out"%(settings.rundir,assembler.upper()))

          print "Printing LAP assembly scores:"
          for assembler in multiple_assemblers:
              print assembler + ": %s"%(assemblerScores[assembler])
              
          print "The assembler with the best LAP score is %s. Continuing pipeline with %s assembler data."%(bestAssembler,bestAssembler)

          shutil.copytree("%s/Assemble/temp%s/out"%(settings.rundir,assembler.upper()),"%s/Assemble/out"%(settings.rundir))

          if bpctgcov:
              pipeline_run([findorfs.FindORFS, \
                       findreps.FindRepeats, annotate.Annotate, abundance.Abundance, \
                       fannotate.FunctionalAnnotation, scaffold.Scaffold, findscforfs.FindScaffoldORFS, \
                       propagate.Propagate, classify.Classify, postprocess.Postprocess],\
                       verbose = 2)
          else:
              pipeline_run([mapreads.MapReads,findorfs.FindORFS, \
                       findreps.FindRepeats, annotate.Annotate, abundance.Abundance, \
                       fannotate.FunctionalAnnotation, scaffold.Scaffold, findscforfs.FindScaffoldORFS, \
                       propagate.Propagate, classify.Classify, postprocess.Postprocess],\
                       verbose = 2)

       #multiprocess threads
       t2 = time.time()
       elapsed = float(t2)-float(t1)

       #print elapsed
       print "done! pipeline took %.2f minutes"%(float(elapsed)/float(60.0))
    except JobSignalledBreak:
       print "Done with errors\n"
