import click, os, re, pymysql.cursors, pyodbc
from lxml import etree
from configparser import ConfigParser as iniparser

#-----
# Main
#-----

@click.group()
def cli():
    """
    Programa de gestión de tareas no gestionadas de en FP Pro.
    """
    pass

@cli.command()
@click.option('--tofile', default=True, type=bool, help='Output to file')
@click.option('--verbose', default=False, type=bool, help='Output to console')
@click.option('--searchtype', default='str', type=click.Choice(['str','blk','job','jobs']), help='Either str, blk, job or jobs')
def list_fittings(searchtype, tofile, verbose):
    '''
    Create list of fittings in str/blk/job(s)
    '''
    var_workpath=fppinikey('SYSTEM',('JOB' if searchtype=='jobs' else searchtype.upper())+'_PATH')
    var_output=[] #Init text output variable
    #Operations to according to selected searchtype
    if searchtype=='job' or searchtype=="jobs":
        if searchtype=='job':
            var_job=click.prompt('Please input job name', type=str)
            click.echo(var_job)
        for root, dirs, files in os.walk(var_workpath):
            for file in files:
                var_fullpath=os.path.join(root, file)
                if searchtype=='job' and file.startswith(var_job.upper()+"_JOBRECORD") and file.endswith(".XML"):
                    var_output.extend(find_fittings_job(var_fullpath))
                elif searchtype=='jobs' and "_JOBRECORD" in file and file.endswith(".XML"):
                    var_output.extend(find_fittings_job(var_fullpath))
    elif searchtype=='str':
        #click.echo('Partially programmed!')
        with click.progressbar(os.walk(var_workpath)) as bar:
            for root, dirs, files in bar:
                for file in files:
                    if file.upper().endswith(".STR"):
                        var_fullpath=os.path.join(root, file)
                        var_output.extend(find_fittings(var_fullpath))
    elif searchtype=='blk':
        #click.echo('Partially programmed!')
        with click.progressbar(os.walk(var_workpath)) as bar:
            for root, dirs, files in bar:
                for file in files:
                    if file.upper().endswith(".BLK"):
                        var_fullpath=os.path.join(root, file)
                        var_output.extend(find_fittings(var_fullpath))
    # Write file?
    if tofile:
        dirname = os.getcwd()
        filename = os.path.join(dirname, 'fittinglist_'+searchtype+'.txt')
        f = open(filename, 'wb')
        f.seek(0)
        f.truncate()
        f.write(bytes(input_output01(var_output), 'utf-8'))
        f.close()
    # Output to console?
    if verbose:
        click.echo(click.style(input_output01(var_output), fg='blue'))

#-------------------
#Internal Operations
#-------------------

def fppinikey(inigroup,inikey):
    '''
    Return specific key value from ini file
    '''
    #Build inifile path
    

    #Initiate parser and parse inifile
    config = iniparser()
    config.read(fppinifile)
    inipath=config[inigroup][inikey]
    return inipath 

def remove_allkits(xmlfile):
    """
    Parse the xml
    """
    parser = etree.XMLParser(strip_cdata=False)
    tree = etree.parse(xmlfile, parser)

    for kit in tree.xpath("//FP_KIT"):
        kit.getparent().remove(kit)

    xml = etree.tostring(tree, encoding="windows-1252", xml_declaration=True, standalone="no", pretty_print=True)
    f = open(xmlfile, 'wb')
    f.seek(0)
    f.truncate()
    f.write(xml)
    f.close()

def find_fittings(xmlfile):
    """
    Parse str/blk xml and return found fittings
    """
    output=[]
    filename=os.path.basename(xmlfile)
    parser = etree.XMLParser(strip_cdata=False)
    tree = etree.parse(xmlfile, parser)
    kitfound=False
    for fit in tree.xpath("//FP_FITTING"):
        if not fit.getparent().tag=="FP_KIT":
            output.append([xmlfile,fit.attrib['Code'],'['+fit.getparent().tag+':'+fit.getparent().attrib['Code']+']'])

    for kit in tree.xpath("//FP_KIT"):
        kitname = kit.attrib['Code']
        #output.append([xmlfile,kit.attrib['Code']])
        if dbtype=='1':
            kitfound=False
            for item in dbkits:
                if item['nomekit']==kitname:
                    output.append([xmlfile,item['codice'],"[FP_KIT:"+kitname+"]"])
                    kitfound=True
                    #click.echo(kitname)
            if kitfound==False:
                output.append([xmlfile,'ERROR',"[FP_KIT_MISSING:"+kitname+"]"])
        elif dbtype=='0':
            kitfound=False
            for row in dbkits:
                if row[0]==kitname:
                    output.append([xmlfile,row[1],"[FP_KIT:"+kitname+"]"])
                    kitfound=True
            if kitfound==False:
                output.append([xmlfile,'ERROR',"[FP_KIT_MISSING:"+kitname+"]"])
    return output

def find_fittings_job(xmlfile):
    """
    Parse jobitem xml and return found fittings
    """
    output=[]
    p=re.compile(r'(\\JOB\\)(\w*)')
    m=p.search(xmlfile)
    if m:
        jobname=m.group(2)
    filename=os.path.basename(xmlfile)
    parser = etree.XMLParser(strip_cdata=False)
    tree = etree.parse(xmlfile, parser)
    #root = tree.getroot()
    item=xmlfile[-6:-4]
    for fit in tree.xpath("//FP_FITTING"):
        output.append(['Job:'+jobname,'Item:'+item,fit.attrib['Code']+'['+fit.getparent().tag+':'+fit.getparent().attrib['Code']+']'])
    return output

#--------------------
# Auxiliary Functions
#--------------------


def input_output01(input):
    """
    Expects a list of lists as input,
    outputs each sublist in a line comma delimited.
    """
    return '\n'.join(','.join(map(str,sl)) for sl in input)

def get_db_kits():
    if dbtype == '1':
        conn=pymysql.connect(host=fppinikey('MYSQL','DB_SERVER_NAME'),
                user=fppinikey('MYSQL','DB_USER'),
                password=fppinikey('MYSQL','DB_PASSWORD'),
                db=fppinikey('MYSQL','DB_NAME'),
                charset='utf8',
                cursorclass=pymysql.cursors.DictCursor)
        try:
            with conn.cursor() as cursor:
                # Read a single record
                #sql = "SELECT `id`, `password` FROM `users` WHERE `email`=%s"
                sql = """
                SELECT kit.nomekit, dettagliokit.codice from dettagliokit inner join kit on kit.pkid = dettagliokit.kitid;
                """
                cursor.execute(sql)
                result = cursor.fetchall()
                #click.echo(result)
                conn.close()
        except Exception as e:
            click.echo(e)
    elif dbtype=='0':
        try:
            conn_str = (
                r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                r'DBQ='+fppaccdbpath+'Fp_Pro32.MDB;'
                )
            click.echo(conn_str)
            cnxn = pyodbc.connect(conn_str)
            crsr = cnxn.cursor()
            sql = """
            SELECT kit.nomekit, dettagliokit.codice from dettagliokit inner join kit on kit.pkid = dettagliokit.kitid;
            """
            result=crsr.execute(sql)
        except Exception as e:
            click.echo(e)
    return result

#----------------------
# Global Variables
#----------------------

fppinifile = os.path.expanduser("~")+'\\AppData\\Roaming\\Emmegisoft\\FP_PRO\\FP_PRO.INI'
fppaccdbpath=fppinikey('SYSTEM','MDB_PATH')
dbtype = fppinikey('SYSTEM','CONN_STR_FP_PRO')
dbkits = get_db_kits()


if __name__=="__main__":
    cli()