import click
import os
import subprocess
import glob

from urllib.request import urlopen
from feedparser import parse
from shutil import copyfileobj
import re

config_dir = os.path.expanduser('~/.docopen')
dirs_file = os.path.join(config_dir, 'directories.txt')
dflt_file = os.path.join(config_dir, 'default_dir.txt')
exts_file = os.path.join(config_dir, 'extensions.txt')
fzfs_file = os.path.join(config_dir, 'fzf_options.txt')
hist_file = os.path.join(config_dir, 'history.txt')

@click.group(invoke_without_command=True)
@click.pass_context
@click.option('-a', '--app')
@click.option('-d', '--dirname', type=click.Path(resolve_path=True))
@click.option('-s', '--stdout', is_flag=True)
@click.option('-f', '--file')
def docopen(ctx, app, dirname, stdout, file):
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
        with open(dirs_file, 'w') as f:
            pass
        with open(dflt_file, 'w') as f:
            pass
        with open(exts_file, 'w') as f:
            f.write('pdf\n')
            f.write('djvu\n')
        with open(fzfs_file, 'w') as f:
            f.write('no-height\n')
            f.write('no-reverse\n')
            f.write('exact\n')
        with open(hist_file, 'w') as f:
            pass
    if file is not None:
        searchfile(file)
    elif ctx.invoked_subcommand is None:
        search(app, dirname, stdout)

@docopen.command()
@click.argument('dirnames', nargs=-1, type=click.Path(resolve_path=True))
def add(dirnames):
    with open(dirs_file, 'a') as f:
        for d in dirnames:
            f.write(d + '\n')

@docopen.command()
@click.argument('dirnames', nargs=-1, type=click.Path(resolve_path=True))
def rm(dirnames):
    with open(dirs_file) as f:
        current_dirs = [l.strip() for l in f.readlines()]
    new_dirs = [d for d in current_dirs if d not in dirnames]
    with open(dirs_file, 'w') as f:
        for d in new_dirs:
            f.write(d + '\n')

@docopen.group()
def extensions():
    pass

@extensions.command()
@click.argument('extensions_names', nargs=-1)
def add(extensions_names):
    with open(exts_file, 'a') as f:
        for e in extensions_names:
            f.write(e + '\n')

@extensions.command()
@click.argument('extensions_names', nargs=-1)
def rm(extensions_names):
    with open(exts_file) as f:
        exts = [l.strip() for l in f.readlines()]
    exts = [e for e in exts if e not in extensions_names]
    with open(exts_file, 'w') as f:
        for e in exts:
            f.write(e + '\n')

@docopen.group()
def fzf():
    pass

@fzf.command()
@click.argument('fzf_options', nargs=-1)
def add(fzf_options):
    with open(fzfs_file, 'a') as f:
        for o in fzf_options:
            f.write(o + '\n')

@fzf.command()
@click.argument('fzf_options', nargs=-1)
def rm(fzf_options):
    with open(fzfs_file) as f:
        fzfs = [l.strip() for l in f.readlines()]
    fzfs = [o for o in fzfs if o not in fzf_options]
    with open(fzfs_file, 'w') as f:
        for o in fzfs:
            f.write(o + '\n')

def show_dirs():
    click.echo()
    click.echo('directories:')
    click.echo('------------')
    with open(dirs_file) as f:
        click.echo(f.read())

def show_exts():
    click.echo()
    click.echo('extensions:')
    click.echo('-----------')
    with open(exts_file) as f:
        click.echo(f.read())

def show_fzfs():
    click.echo()
    click.echo('fzf options:')
    click.echo('------------')
    with open(fzfs_file) as f:
        for line in f.readlines():
            click.echo(line.strip('\n'))

def show_hist(summary=True):
    click.echo()
    click.echo('history:')
    click.echo('--------')
    if summary:
        with open(hist_file) as f:
            number_of_entries = len(f.readlines())
        click.echo(f'{number_of_entries} entries')
        click.echo('run `docopen info --history` to print them all.')
    if not summary:
        with open(hist_file) as f:
            click.echo(f.read())

@docopen.command()
@click.option('-a', '--all',       is_flag=True)
@click.option('-d', '--directory', is_flag=True)
@click.option('-e', '--extension', is_flag=True)
@click.option('-f', '--fzf-options', is_flag=True)
@click.option('-h', '--history',   is_flag=True)
def info(all, directory, extension, fzf_options, history):
    if not all and not directory and not extension and not history:
        show_dirs()
        show_exts()
        show_fzfs()
    elif all:
        show_dirs()
        show_exts()
        show_fzfs()
        show_hist()
    else:
        if directory:
            show_dirs()
        if extension:
            show_exts()
        if fzf_options:
            show_fzfs()
        if history:
            show_hist(summary=False)

@docopen.command()
@click.option('-a', '--all',       is_flag=True)
@click.option('-d', '--directory', is_flag=True)
@click.option('-e', '--extension', is_flag=True)
@click.option('-f', '--fzf-options', is_flag=True)
@click.option('-h', '--history',   is_flag=True)
def clear(all, directory, extension, fzf_options, history):
    if not all and not directory and not extension and not fzf_options and not history:
        click.echo('see --help')
    elif all:
        open(dirs_file, 'w').close()
        open(exts_file, 'w').close()
        open(fzfs_file, 'w').close()
        open(hist_file, 'w').close()
    else:
        if directory:
            open(dirs_file, 'w').close()
        if extension:
            open(exts_file, 'w').close()
        if fzf_options:
            open(fzfs_file, 'w').close()
        if history:
            open(hist_file, 'w').close()

def isdoc(file, exts):
    extension = os.path.splitext(file)[1].lower()
    if extension in exts:
        return True
    return False

def get_doc_paths(dirs, exts):
    paths = []
    for d in dirs:
        for w in os.walk(d):
            docs = [l for l in w[2] if isdoc(l, exts)]
            paths += [os.path.join(w[0], doc) for doc in docs]
    return paths

def remove_repetitions(old_list):
    indices = [old_list.index(e) for e in list(set(old_list))]
    indices.sort()
    new_list = [old_list[i] for i in indices]
    return new_list

def reorder_from_history(list_to_reorder, history):
    indices = []
    for l in history:
        try:
            indices.append(list_to_reorder.index(l))
        except ValueError:
            pass
    reordered_list = []
    for i in indices:
        reordered_list.append(list_to_reorder[i])
    for i in range(len(list_to_reorder)):
        if i not in indices:
            reordered_list.append(list_to_reorder[i])
    return reordered_list

def add_extension(name, extension):
    extension = extension.lower().strip('.')
    if extension != 'pdf':
        name += f' [{extension}]'
    return name

def formatdoc(doc):
    filename = os.path.basename(doc)
    name, extension = os.path.splitext(filename)
    splittedname = name.split(' - ')
    if len(splittedname) == 1:
        formattedname = add_extension(name, extension)
        return formattedname
    authors = splittedname[0]
    title = ' - '.join([part.replace('-', ' ') for part in splittedname[1:]])
    for c in [',', '.', '&', '-']:
        authors = authors.replace(c, ' ')
    authors = ' '.join(authors.split())
    title = title.lower()
    formattedname = (authors + '  |  ' + title)
    formattedname = add_extension(formattedname, extension)
    return formattedname

def searchfile(file):
    with open(file) as f:
        docs = sorted(f.read().splitlines(), reverse=True)

    with open(fzfs_file) as f:
        fzfs = ' '.join(['--' + l  for l in f.readlines()])

    lines = ''
    for i, doc in enumerate(docs):
        lines += f'{i} {formatdoc(doc)}\n'
    cmd = 'fzf --with-nth 2.. +s ' + fzfs
    output = subprocess.run(cmd.split(), input=lines, text=True,
            stdout=subprocess.PIPE).stdout
    if len(output) == 0:
        return
    index = int(output.split()[0])

    with open(dirs_file) as f:
        dirs = [line.strip('\n') for line in f.readlines()]

    with open(exts_file) as f:
        exts = ['.' + line.strip('\n') for line in f.readlines()]

    for d in dirs:
        for w in os.walk(d):
            for l in w[2]:
                if l == docs[index]:
                    path = os.path.join(w[0], l)
                    subprocess.run(['open', path])
                    return
    click.echo('file not found')


def search(app, dirname, stdout):
    if dirname is None:
        with open(dirs_file) as f:
            dirs = [line.strip('\n') for line in f.readlines()]
    else:
        dirs = [dirname]

    with open(exts_file) as f:
        exts = ['.' + line.strip('\n') for line in f.readlines()]

    with open(fzfs_file) as f:
        fzfs = ' '.join(['--' + l  for l in f.readlines()])

    while True:
        with open(hist_file) as h:
            hist = [l.strip('\n') for l in h.readlines()][::-1]
        hist = remove_repetitions(hist)

        doc_paths = get_doc_paths(dirs, exts)
        doc_paths = reorder_from_history(doc_paths, hist)

        lines = ''
        for i, doc in enumerate(doc_paths):
            lines += f'{i} {formatdoc(doc)}\n'
        cmd = 'fzf --with-nth 2.. +s ' + fzfs
        output = subprocess.run(cmd.split(), input=lines, text=True,
                stdout=subprocess.PIPE).stdout

        if len(output) > 0:
            index = int(output.split()[0])
            file = doc_paths[index]
            if stdout:
                click.echo(os.path.basename(file))
                break
            elif app == None:
                subprocess.run(['open', file])
            else:
                subprocess.run(['open', '-a' + app, file])
            if dirname is None:
                with open(hist_file, 'a') as h:
                    h.write(file + '\n')
        if len(output) == 0 or dirname is not None:
            break


#############
### ARXIV ###
#############

def getfeed(arxivid):
    url = 'http://export.arxiv.org/api/query?id_list=' + arxivid
    feed = urlopen(url)
    arxivfeed = parse(feed)['entries'][0]
    return arxivfeed

def parse_arxiv_feed(arxivfeed):
    title = arxivfeed['title']
    authors = [a['name'] for a in arxivfeed['authors']]
    pdf_url = arxivfeed['links'][1]['href']
    return title, authors, pdf_url

def change_title(title):
    # replace spaces with dashes
    title = title.replace(' ', '-')
    # replace slaches by dashes
    title = title.replace('/', '-')
    # remove multiple occurences of dashes
    title = re.sub(r'(\W)\1+', r'\1', title)
    # delete characters
    for c in ['\n', ',', '.', '$', ':']:
        title = title.replace(c, '')
    # lower case
    title = title.lower()

    return title

def authors_to_string(authors):
    # Only take the last name
    modified_authors = []
    for a in authors:
        # take last name only
        a = a.split(' ')[-1].capitalize()
        # Capitalize
        a = a.capitalize()
        modified_authors.append(a)
    return '-'.join(modified_authors)

def make_pdf_file_name(authors, title, separation=' - '):
    """
        authors: list
        title: string
        splitting: string
    """
    file_name = authors_to_string(authors)
    file_name += separation
    file_name += change_title(title)
    file_name += '.pdf'
    return file_name

@docopen.command()
@click.argument('arxivid')
@click.option('-d', '--dirname', type=click.Path(resolve_path=True))
def aget(arxivid, dirname):
    if dirname is None:
        with open(dflt_file) as f:
            dirname = f.readline().strip('\n')

    arxivfeed = getfeed(arxivid)
    title, authors, pdf_url = parse_arxiv_feed(arxivfeed)

    filename = make_pdf_file_name(authors, title)
    outputfile = os.path.join(dirname, filename)

    # download the pdf
    req = urlopen(pdf_url)
    with open(outputfile, 'wb') as fp:
        copyfileobj(req, fp)

    # print the name of the output file
    click.echo(outputfile)

    # open the pdf
    os.system(f'open "{outputfile}"')


###########
### ldn ###
###########

def get_lastest_file(directory):
    files = glob.glob(os.path.join(directory, '*'))
    if len(files) > 0:
        lastest_file = max(files, key=os.path.getctime)
        return lastest_file
    else:
        return None

def get_authors_and_title(filename):
    message = click.edit(text=f'{filename}\nauthors:\n\ntitle:\n',
                            editor='atom --wait')
    lines = message.splitlines()
    authors = lines[2].split()
    title = lines[4]
    return authors, title

@docopen.command()
@click.option('-d', '--dirname', type=click.Path(resolve_path=True))
@click.option('-s', '--source', type=click.Path(resolve_path=True))
def ldn(dirname, source):
    if dirname is None:
        with open(dflt_file) as f:
            dirname = f.readline().strip('\n')
    if source is None:
        source = os.path.expanduser('~/Downloads')

    last_download = get_lastest_file(source)
    if last_download is None:
        click.echo('no file found')
        raise click.Abort
    else:
        click.echo('source: ' + os.path.basename(last_download))
        click.echo('target: ' + dirname)
    click.confirm('move?', abort=True, default=True)
    filename = os.path.splitext(os.path.basename(last_download))[0]
    authors, title = get_authors_and_title(filename)
    target = os.path.join(dirname, make_pdf_file_name(authors, title))
    click.echo(target)
    os.rename(last_download, target)
    if open:
        subprocess.run(['open', target])
