import re
from pprint import pprint

def test_modify_label(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": "Kappa@fr"
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    responselist = client.post('/admin/project/testproject', json={
        "label": ["Kappa@fr", "test@de"]
    }, headers=header)
    res = responselist.json
    print(res)
    assert responselist.status_code == 200
    responselist2 = client.get('/admin/project/testproject', headers=header)
    res = responselist2.json
    print(res)
    assert res.get('label') == ['Kappa@fr', 'test@de']

    responsedict = client.post('/admin/project/testproject', json={
        "label": {"add": ["Kappa@it"], "del": ["test@de"]}
    }, headers=header)
    res = responsedict.json
    print(res)
    assert responsedict.status_code == 200
    responsedict2 = client.get('/admin/project/testproject', headers=header)
    res = responsedict2.json
    print(res)
    assert res.get('label') == ['Kappa@fr', "Kappa@it"]

def test_modify_label_replaced(client, token_headers, testproject):
    header = token_headers[1]
    response = client.post('/admin/project/testproject', json={
        "label": {'add': ["Kappa@de"], 'del': ["unittest@de"]}
    }, headers=header)
    res = response.json
    print(res)
    responsedict2 = client.get('/admin/project/testproject', headers=header)
    res = responsedict2.json
    print(res)


def test_modify_comment(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "comment": "random changed comment@en"
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    responselist = client.post('/admin/project/testproject', json={
        "comment": ["random changed comment@en", "another comment@de"]
    }, headers=header)
    res = responselist.json
    print(res)
    assert responselist.status_code == 200
    responselist2 = client.get('/admin/project/testproject', headers=header)
    res = responselist2.json
    print(res)
    assert res.get('comment') == ["random changed comment@en", "another comment@de"]

    responsedict = client.post('/admin/project/testproject', json={
        "comment": {"add": ["newcomment@it"], "del": ["another comment@de"]}
    }, headers=header)
    res = responsedict.json
    print(res)
    assert responsedict.status_code == 200
    responsedict2 = client.get('/admin/project/testproject', headers=header)
    res = responsedict2.json
    print(res)
    assert res.get('comment') == ['random changed comment@en', 'newcomment@it']


def test_modify_bad_label_number(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": 1234
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_bad_label_string(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": "kappa"
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_bad_label_array(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": ["gugugugu", "gagagagagag@en"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

def test_modify_bad_label_wrong_command(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"crap": "gugugugu", "alsocrap": "gagagagagag@en"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_lang_default(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"add": ["u"], "del": ["gagagagagag@en"]}
    }, headers=header)
    assert response.status_code == 200
    responsedict2 = client.get('/admin/project/testproject', headers=header)
    res = responsedict2.json
    assert 'u@en' in res['label']

def test_modify_label_lang_default_addsign(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"add": ["u@asdfgasdg"], "del": ["gagagagagag@en"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_lang_add(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"add": ["u@at"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json

def test_modify_label_del_nonexistent(client, token_headers, testproject):
    # TODO: Is error code 500 correct? Shouldn't it be 400?
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"del": ["doesnotexist@zu"]}
    }, headers=header)
    assert response.status_code == 500
    res = response.json
    print(res)

def test_modify_label_set_val_deflang(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": ["u"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

def test_modify_label_add_without_lang(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"add": "u"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_without_lang(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"del": "u"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_add_without_lang_b(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"del": ["uasdf"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_without_lang_c(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"del": ["u"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_invalid_lang(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"del": ["u@at"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_delete(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": None
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

def test_modify_label_empty_list(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": []
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_list_none(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": [None]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_replace_invalid_lang(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": ["kappa@zz"]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_empty_dict(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_add_list_none(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"add": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_add_empty_list(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"add": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_empty_list(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"del": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_list_none(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": {"del": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_bad_comment(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "comment": 1234
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_comment_xxx(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "comment": "kappa"
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": ["gugugugu", "gagagagagag@en"]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"crap": "gugugugu", "alsocrap": "gagagagagag@en"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"add": ["u"], "del": ["gagagagagag@en"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"add": ["u@asdfgasdg"], "del": ["gagagagagag@en"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"add": ["u@at"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"del": ["doesnotexist@zu"]}
    }, headers=header)
    assert response.status_code == 500
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"del": ["doesnotexist@at"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": ["d"]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"add": "abc@de"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": "abc@de"
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"del": ["abc"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"del": ["a"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"del": "a@de"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": None
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": []
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": [None]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": ["kappa@zz"]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"add": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"add": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"del": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/project/testproject', json={
        "comment": {"del": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_startdate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectStart": "1995-05-28"
    }, headers=header)

    assert response.status_code == 200
    response2 = client.get('/admin/project/testproject', headers=header)
    res = response2.json
    assert res['projectStart'] == "1995-05-28"


def test_modify_bad_startdate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectStart": "2024-05-28-88<code>kappa</code>"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_enddate(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectEnd": "2024-05-28"
    }, headers=header)

    assert response.status_code == 200
    response2 = client.get('/admin/project/testproject', headers=header)
    res = response2.json
    assert res['projectEnd'] == "2024-05-28"


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/project/testproject', json={
        "label": "Kappa@fr"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.get('/admin/project/getid', query_string={
        "iri": "kappa"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_modify_immutable(client, token_headers):
    header = token_headers[1]

    projectshortName = client.post('/admin/project/testproject', json={
        "projectShortName": "randomprojectname"
    }, headers=header)
    assert projectshortName.status_code == 400
    res = projectshortName.json

    projectIri = client.post('/admin/project/testproject', json={
        "projectIri": "randomprojectIri"
    }, headers=header)
    assert projectIri.status_code == 400
    res = projectIri.json

    namespaceIri = client.post('/admin/project/testproject', json={
        "namespaceIri": "randomnamespaceIri"
    }, headers=header)
    assert namespaceIri.status_code == 400
    res = namespaceIri.json


def test_project_to_modify_not_found(client, token_headers):
    header = token_headers[1]

    response = client.post('/admin/project/notexistingproject', json={
        "label": ["Kappa@fr"]
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == 'Project with IRI/shortname "notexistingproject" not found.'


def test_no_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/project/testproject', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_empty_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/project/testproject', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_no_permission_modify(client, token_headers, testproject):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Kappauser",
        "familyName": "KappaKappatest",
        "email": "kappa@kappa.com",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ],
        "hasPermissions": [
            "GenericRestricted"
        ]
    }, headers=header)

    login = client.post('/admin/auth/rosmankappa', json={'password': 'kappa1234'})
    token = login.json['token']
    headers = {
        'Authorization': f'Bearer {token}'
    }

    response2 = client.post('/admin/project/testproject', json={
        "label": ["Kappa@de"]
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403


def test_modify_inconsistent_dates(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectEnd": "1992-04-05"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    response2 = client.get('/admin/project/testproject', headers=header)
    print(response2.text)


def test_randomstuff(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "label": ""
    }, headers=header)

    # assert response.status_code == 400
    res = response.json
    print(res)
    response2 = client.get('/admin/project/testproject', headers=header)
    print(response2.text)


def test_json_with_unknown_fields(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "kappa": "Gaga\"++-usw@en"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
