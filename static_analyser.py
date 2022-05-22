from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import subprocess
import linecache
import re

app = FastAPI()


templates = Jinja2Templates(directory="templates")


def run_command(file_name, *command_args):
    process = subprocess.Popen(
        [*command_args, file_name],
        stdout=subprocess.PIPE, encoding='utf-8')
    return process.communicate()


def flake_parser(file_name):
    run_output = run_command(file_name, "flake8")
    id_ = {}
    for n, result in enumerate(run_output[0].strip().split('\n')):
        if not result or not result.strip():
            continue
        issue = ' '.join(result.split()[2:])
        line_number = int(result.split()[0].split(':')[1])
        particular_line = linecache.getline(file_name, line_number)
        id_[issue.capitalize()] = {
            "num": f"{str(n)}_flake",
            "particular_line": particular_line,
            "line_no": line_number,
            "parser": "flake8"
        }
    return id_


def bandit_parser(file_name):
    run_output = run_command(file_name, "bandit", "-r")
    id_ = {}
    for output in run_output:

        if not output or '>> Issue:' not in output:
            continue
        issues = output.split('>> Issue:')
        for iss in issues:
            issue_compressed = re.findall(r'\[[A-Z0-9]+\:[a-z_0-9]+\]', iss)
            id_.update(bandit_issue_parser(iss, issue_compressed, file_name))
    return id_


def bandit_issue_parser(iss, issue_compressed, file_name):
    id_ = {}
    for iss_c in issue_compressed:
        if not iss_c:
            continue
        iss_description_unparsed = iss.split(iss_c)
        for n, des_un in enumerate(iss_description_unparsed):
            if not des_un or not des_un.strip():
                continue
            issue_title = des_un.strip().split('Severity')[0].strip()
            line_number = re.findall(
                r'Location:(.*?).py:(\d+):\d+', des_un)[0][1]
            line_number = int(line_number[0])

            particular_line = linecache.getline(file_name, line_number)
            id_[issue_title] = {
                "num": f"{str(n)}_bandit",
                "particular_line": particular_line,
                "line_no": line_number,
                "parser": "bandit"
            }
    return id_


@app.get("/file/{file_name}", response_class=HTMLResponse)
async def read_item(request: Request, file_name: str):
    print(file_name)
    id_ = flake_parser(file_name)
    id_.update(bandit_parser(file_name))

    return templates.TemplateResponse("item.html", {
        "request": request,
        "id": id_})
