import click
import os
import subprocess

config_dir = os.path.expanduser('~/.docopen')
dirs_file = os.path.join(config_dir, 'directories.txt')
exts_file = os.path.join(config_dir, 'extensions.txt')
fzfs_file = os.path.join(config_dir, 'fzf_options.txt')
hist_file = os.path.join(config_dir, 'history.txt')

@click.group(invoke_without_command=True)
@click.pass_context
@click.option('-a', '--app')
@click.option('-d', '--dirname', type=click.Path(resolve_path=True))
def docopen(ctx, app, dirname):
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)
        with open(dirs_file, 'w') as f:
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
    if ctx.invoked_subcommand is None:
        search(app, dirname)

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

def search(app, dirname):
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
            lines += f'{i} {os.path.basename(doc)}\n'
        cmd = 'fzf --with-nth 2.. +s ' + fzfs
        output = subprocess.run(cmd.split(), input=lines, text=True,
                stdout=subprocess.PIPE).stdout
        if len(output) > 0:
            index = int(output.split()[0])
            file = doc_paths[index]
            if app == None:
                subprocess.run(['open', file])
            else:
                subprocess.run(['open', '-a' + app, file])
            if dirname is None:
                with open(hist_file, 'a') as h:
                    h.write(file + '\n')
        if len(output) == 0 or dirname is not None:
            break
