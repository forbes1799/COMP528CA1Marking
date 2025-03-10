import click
import pathlib
import os
from slurm import submit_slurm_job
from executor import run_command

executables = [{'compile_command': "make gccomp", 'name': "gccomp", 'args': ['{basedir}/asteroids_train.csv', '{basedir}asteroids_test.csv', '{basedir}sout.csv', '3']},
               {'compile_command': "make iccomp", 'name': "iccomp", 'args': ['{basedir}/asteroids_train.csv', '{basedir}asteroids_test.csv', '{basedir}sout.csv', '3']}]


def compile(basedir, artifacts_path):
    successful_compilations = []

    for exe in executables:
        command = exe['compile_command']
        e = exe["name"]
        command = command.format_map({'basedir' : basedir})
        output_file_name = "%s_compilation.out" % e
        output_file_path = os.path.join(basedir, output_file_name)
        p = run_command(command, cwd=basedir, output_file=output_file_path)
        rc = p.returncode
        if rc == 0:
            path_to_executable = os.path.join(basedir, e)
            exe["full_path"] = path_to_executable
            successful_compilations.append(exe)
    
    return successful_compilations


def submit_job_for_run(exe, num_threads, identifier, artifacts_path, basedir):
    args = [x.format_map({'basedir': basedir}) for x in exe["args"]]
    results_file_name = os.path.join(basedir, "iresults.csv")
    command_to_run = ["python", os.path.join(artifacts_path, "single-instance-runner.py")]
    command_to_run += ["--num-threads", str(num_threads)]
    command_to_run += ["--identifier", str(identifier)]
    command_to_run += ["--results-file", results_file_name]
    command_to_run += ["--executable", "%s,%s" % (exe["full_path"], ",".join(args))]

    command_to_run = " ".join(command_to_run)
    slurm_template = os.path.join(artifacts_path, "slurm_template.tpl")
    return submit_slurm_job([command_to_run], slurm_template, cwd=basedir,
                            time_limit=20, num_cores=num_threads)

@click.command()
@click.option('--basedir', default=None, help='Directory to find executables')
@click.option('--identifier', required=True, help='Identify this submission')
@click.option('--artifacts-path', default=None, help='Location of artifacts')
def run(basedir, identifier, artifacts_path):
    if artifacts_path is None:
        artifacts_path = pathlib.Path(__file__).parent.resolve()
    
    basedir = os.path.abspath(basedir)
    
    executables = compile(basedir, artifacts_path)

    max_threads = 33
    thread_nums = []
    threadnum = 1
    while threadnum < max_threads:
        thread_nums.append(threadnum)
        threadnum *= 2
    thread_nums = list(reversed(thread_nums))

    job_ids = []
    for e in executables:
        for c in thread_nums:
            job_id = submit_job_for_run(e, c, identifier, artifacts_path, basedir)
            job_ids.append(job_id)
    # submit_job_for_collation(job_ids)


if __name__=="__main__":
    run()