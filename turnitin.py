import json
import mimetypes
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import time
import re
import io

__LOGIN_URL = "https://www.turnitin.com/login_page.asp?lang=en_us"
__HOMEPAGE = "https://www.turnitin.com/s_home.asp"
__DOWNLOAD_URL = "https://www.turnitin.com/paper_download.asp"
__SUBMIT_URL = "https://www.turnitin.com/t_submit.asp"
__CONFIRM_URL = "https://www.turnitin.com/submit_confirm.asp"
__HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "sec-ch-ua": '"Chromium";v="85", "\\\\Not;A\\"Brand";v="99", "Microsoft Edge";v="85"',
    "content-type": "application/x-www-form-urlencoded",
    "referer": __LOGIN_URL,
    "referrer": __LOGIN_URL,
    "referrerPolicy": "no-referrer-when-downgrade",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
}


def login(email, password):
    s = __newSession()
    payload = f"javascript_enabled=0&email={email}&user_password={password}&submit=Log+in".encode(
        "utf-8"
    )
    cookies = __getCookies(s, __LOGIN_URL)
    __setCookies(s, cookies)
    __post(s, __LOGIN_URL, payload)
    return cookies.get_dict()


def getClasses(cookies):
    s = __newSession()
    __setCookies(s, cookies)
    source = __get(s, __HOMEPAGE)
    classes = __parseDashboard(source)
    return classes


def __getUserId(source):
    soup = BeautifulSoup(source, 'html.parser')
    script = soup.find('script', text=re.compile('globalContextObject'))

    if script:
        match = re.search(r'"userId":\s*"trn:user:us:tfs::(\d+)"', script.string)
        if match:
            return match.group(1)

    return None
    pass


def getAssignments(url, cookies):
    s = __newSession()
    __setCookies(s, cookies)
    source = __get(s, url)
    user_id = __getUserId(source)
    table = __getAssignmentTable(source)
    return [
        {
            "title": __getAssignmentTitle(assignment),
            "type": __getAssignmentType(assignment),
            "dates": __getAssignmentDate(assignment),
            "submission": __getSubmissionLink(assignment),
            "user_id": user_id,
            "ass_id": __getAssignmentId(assignment)
        }
        for assignment in table
    ]


def file_upload(cookies, ass_id, user_id, file_url):
    mimetypes.init()
    url = f"https://www.turnitin.com/api/lti/1p0/redirect/upload_submission/{ass_id}/{user_id}"
    cookie_string = '; '.join([f"{key}={value}" for key, value in cookies.items()])
    response = requests.get(file_url)
    file = io.BytesIO(response.content)
    print(len(file.getvalue()))

    file_name = file_url.split('/')[-1]
    print(file_name)
    mime_type, _ = mimetypes.guess_type(file_name)

    # If the MIME type couldn't be guessed, default to 'application/octet-stream'
    if mime_type is None:
        mime_type = 'application/octet-stream'

    print(mime_type)


    payload = {
        'submission_title': file_name,
        'submission_filename': file_name
    }

    files = {
        'fileupload': (file_name, file,mime_type)
    }

    headers = {
        'Cookie': cookie_string,
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)'
    }

    response = requests.request("POST", url, headers=headers, data=payload, files=files)

    return json.loads(response.text)


def submit(
    cookies,
    file_upload_id,
    ass_id,
    user_id,
):
    cookie_string = '; '.join([f"{key}={value}" for key, value in cookies.items()])
    print(cookie_string)
    url = f"https://www.turnitin.com/api/lti/1p0/redirect/upload_save_request/{file_upload_id}/{ass_id}?lang=en_us&author_id={user_id}&placeholder=0"

    payload = {}
    headers = {
        'Cookie': 'legacy-session-id=5f732217ef634942af09d1a081cb0db0;session-id=5f732217ef634942af09d1a081cb0db0',
        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)'
    }
    time.sleep(5)
    response = requests.request("POST", url, headers=headers, data=payload)
    if json.loads(response.text).get("error") == 'Your submission must contain 20 words or more.':
        print("Wait for 5 seconds...")
        time.sleep(5)
        response = requests.request("POST", url, headers=headers, data=payload)

    return json.loads(response.text)


def __newSession():
    return requests.Session()


def __parseDashboard(source):
    soup = BeautifulSoup(source, "html.parser")
    classes = soup.find_all("td", {"class": "class_name"})
    for i in range(len(classes)):
        e = classes[i].find("a")
        classes[i] = {
            "title": e["title"],
            "url": f"https://www.turnitin.com{e['href']}",
        }
    return classes


def __resetHeaders(s):
    s.headers.update(__HEADERS)


def __post(s, url, payload):
    __resetHeaders(s)
    return s.post(url, data=payload).content.decode("utf-8")


def __get(s, url):
    __resetHeaders(s)
    return s.get(url).content.decode("utf-8")


def __getCookies(s, url):
    s.get(url)
    cookies = s.cookies
    return cookies


def __setCookies(s, cookies):
    s.cookies.update(cookies)


def __getAssignmentTitle(e):
    title_td = e.find("td", {"class": "title-column"})
    if title_td:
        title_div = title_td.find("div", {"class": "ellipsis"})
        if title_div:
            return title_div.text.strip()
    return "Title not found"


def __getAssignmentType(e):
    type_column = e.find("td", {"class": "type-column"})
    if type_column:
        type_label = type_column.find("span", {"class": "type-label"})
        if type_label:
            return type_label.text.strip()
    return "Type not found"


def __convertDate(epoch):
    if epoch is not None:
        return datetime.fromtimestamp(int(epoch)).strftime('%Y-%m-%d %H:%M:%S')
    return None

def __getAssignmentDate(e):
    dates_column = e.find("td", {"class": "dates-column student-dates-cell"})
    if dates_column:
        date_rows = dates_column.find("table", {"class": "student-dates-table"}).find_all("tr")
        return {
            "start": __convertDate(date_rows[0].get("data-date-epoch")),
            "due": __convertDate(date_rows[1].get("data-date-epoch")),
            "post": __convertDate(date_rows[2].get("data-date-epoch"))
        }
    return {"start": None, "due": None, "post": None}


def __getSubmissionLink(e):
    open_column = e.find("td", {"class": "open-column"})
    if open_column:
        open_link = open_column.find("a", {"class": "btn btn-primary btn-open"})
        if open_link:
            return open_link['href']
    return "Link not found"

def __getAssignmentId(e):
    open_column = e.find("td", {"class": "open-column"})
    if open_column:
        open_link = open_column.find("a", {"class": "btn btn-primary btn-open"})
        if open_link:
            return re.search("(\d+)", open_link['href']).group(1)
    return "ID not found"


def __getAid(e):
    return re.search("(\d+)", e["id"]).group(1)


def __getOid(e):
    try:
        pattern = re.compile("(\d+)")
        # print(f"[DEBUG] Searching {e.find('a')['id']} for {pattern}")
        return re.search(pattern, e.find("a")["id"]).group(1)
    except KeyError:
        return "void"
    except AttributeError:
        # print(f"[DEBUG] {e} of type {type(e)} does not seem to have a .find()")
        return "void"


def __getFileName(e):
    pattern = re.compile("fn=(.+)\\&.+\\&")
    try:
        # print(f"[DEBUG] Searching {e} for {pattern}")
        return re.search(pattern, str(e)).group(1)
    except KeyError:
        # uin = ''
        # QUIT = 0
        # while uin != "QUIT":
        #     try:
        #         uin = input(">>> ")
        #         eval(uin)
        #     except:
        #         pass
        # print(f"[DEBUG] Fuck you bich (from __getFileName(e))")
        return "void"
    except AttributeError:
        # print(f"[DEBUG] {e} of type {type(e)} does not seem to have a .find()")
        return "void"


def __getMenu(e):
    return e.find("ul", {"class": "dropdown-menu"})


def __getAssignmentTable(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("tr", {"class": ("Paper", "Revision","assignment-row")})

def __getAuthorName(html):
    soup = BeautifulSoup(html, "html.parser")
    return (
        soup.find_all("div", {"class": "form-group"})[0].find("input")["value"],
        soup.find_all("div", {"class": "form-group"})[1].find("input")["value"]
    )
