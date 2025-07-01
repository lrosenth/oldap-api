def test_modify_label_A(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": "Kappa@fr"
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_label_B(client, token_headers, testpermissionset):
    header = token_headers[1]

    responselist = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["Kappa@fr", "test@de"]
    }, headers=header)
    res = responselist.json
    print(res)
    assert responselist.status_code == 200
    responselist2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = responselist2.json
    print(res)
    assert set(res.get('label')) == {'Kappa@fr', 'test@de'}

def test_modify_label_C(client, token_headers, testpermissionset):
    header = token_headers[1]

    responsedict = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"add": ["Kappa@it"], "del": ["test@de"]}
    }, headers=header)
    res = responsedict.json
    print(res)
    assert responsedict.status_code == 200
    responsedict2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = responsedict2.json
    print(res)
    assert set(res.get('label')) == {'testPerm@en', "Kappa@it"}


def test_modify_comment_A(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": "random changed comment@en"
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_comment_B(client, token_headers, testpermissionset):
    header = token_headers[1]

    responselist = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": ["random changed comment@en", "another comment@de"]
    }, headers=header)
    res = responselist.json
    print(res)
    assert responselist.status_code == 200
    responselist2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = responselist2.json
    print(res)
    assert set(res.get('comment')) == {"random changed comment@en", "another comment@de"}

def test_modify_comment_C(client, token_headers, testpermissionset):
    header = token_headers[1]

    responsedict = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"add": ["newcomment@it"], "del": ["another comment@de"]}
    }, headers=header)
    res = responsedict.json
    print(res)
    assert responsedict.status_code == 200
    responsedict2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = responsedict2.json
    print(res)
    assert set(res.get('comment')) == {'For testing@en', 'newcomment@it'}


def test_modify_gives_permission(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "givesPermission": "DATA_VIEW"
    }, headers=header)

    assert response.status_code == 200

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('givesPermission') == 'DATA_VIEW'


def test_modify_bad_label(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": 1234
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_string(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": "kappa"
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_replace_double_lang(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["gugugugu", "gagagagagag@en"]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('label') == ["gagagagagag@en"]


def test_modify_label_invalid_key(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"crap": "gugugugu", "alsocrap": "gagagagagag@en"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_add_del(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"add": ["u"], "del": ["gagagagagag@en"]}
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('label')) == {"u@en", "test@de"}


def test_modify_label_add_del_b(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"add": ["u@asdfgasdg"], "del": ["gagagagagag@en"]}
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('label')) == {"u@asdfgasdg@en", "test@de"}


def test_modify_label_add_invalid_lang(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"add": ["u@at"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_uniexisting(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"del": ["doesnotexist@zu"]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_invalid_lang(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["kappa@zz"]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_empty_list(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": []
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_list_none(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": [None]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_empty_dict(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_add_empty_list(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"add": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_add_list_none(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"add": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_empty_list(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"del": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_list_none(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"del": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_add_empty_list(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"add": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_list_none(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"add": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_empty_list(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"del": []}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_label_del_list_none(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"del": [None]}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_bad_comment(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": 1234
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_bad_comment_number(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": "kappa"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_comment_double_lang(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": ["gugugugu", "gagagagagag@en"]
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('comment')) == {"gagagagagag@en"}


def test_modify_comment_invalid_key(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"crap": "gugugugu", "alsocrap": "gagagagagag@en"}
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_comment_add_del(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"add": ["u"], "del": ["gagagagagag@en"]}
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('comment')) == {"u@en", "Für Tests@de"}


def test_modify_comment_add_double(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"add": ["u@asdfgasdg"], "del": ["gagagagagag@en"]}
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('comment')) == {"u@asdfgasdg@en", "Für Tests@de"}


def test_modify_comment_add_invalid_lang(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"add": ["u@at"]}
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_comment_del_inexisting_lang(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"del": ["doesnotexist@zu"]}
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_comment_del_inexisting(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"del": ["doesnotexist@at"]}
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_comment_replace_inexisting_lang(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": ["gugugugu@zz"]
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_bad_givespermission(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "givesPermission": 1234
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_empty_label(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": ["random comment@de"],
        "givesPermission": "DATA_VIEW"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('comment')) == {"random comment@de"}
    assert res.get('givesPermission') == "DATA_VIEW"



def test_modify_empty_comment(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "givesPermission": "DATA_VIEW"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('label')) == {"testPerm@en", "test@Perm@de"}
    assert res.get('givesPermission') == "DATA_VIEW"



def test_modify_empty_givespermission(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["testPerm@en", "test@Perm@de"],
        "comment": ["random comment@it"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('label')) == {"testPerm@en", "test@Perm@de"}
    assert set(res.get('comment')) == {"random comment@it"}



def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": "Kappa@fr"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_permissionset_to_modify_not_found(client, token_headers):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/notexistingproject', json={
        "label": "Kappa@fr"
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == 'No permission set "oldap:notexistingproject"'


def test_no_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/permissionset/oldap/testpermissionset', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_empty_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/permissionset/oldap/testpermissionset', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_json_with_unknown_fields(client, token_headers, testproject):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "kappa": "Gaga\"++-usw@en"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_bad_langstring(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": 123,
        "givesPermission": "DATA_UPDATE",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_no_permission_modify(client, token_headers, testpermissionset):
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

    response2 = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["Kappa@fr"],
        "comment": ["random comment@it"],
        "givesPermission": "DATA_UPDATE"
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403


def test_modify_label_weird(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {
            "add": ["spaghetti@it", "zuzu@zu"],
            "del": ["testPerm@en"]
        },
    }, headers=header)

    assert response.status_code == 200

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('label')) == {'test@de', 'spaghetti@it', 'zuzu@zu'}


def test_modify_label_short_language_tag(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["u"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('label')) == {'u@en'}

def test_modify_label_del_nolist(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"del": "u@de"},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The given attributes in add and del must be in a list"


def test_modify_label_string(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": "uasdf",
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_label_add_string(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"add": "uasdf"},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_label_no_language_tag(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": ["uasdf"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert set(res.get('label')) == {'uasdf@en'}


def test_modify_label_del_no_language_tag(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"del": ["uasdf"]},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_label_del_too_short(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"del": ["u"]},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_label_del_tag_unknown(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": {"del": ["u@at"]},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_del_whole_label(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "label": None,
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('label') == None



def test_modify_comment_short_language_tag(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": ["u"],
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('comment') == ['u@en']



def test_modify_comment_no_list(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"add": "u"},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_comment_del_no_list(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"del": "u"},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_comment_del_no_lang_tag(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"del": ["uasdf"]},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_comment_del_short_lang_tag(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": {"del": ["u"]},
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_del_whole_comment(client, token_headers, testpermissionset):
    header = token_headers[1]

    response = client.post('/admin/permissionset/oldap/testpermissionset', json={
        "comment": None,
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

    response2 = client.get('/admin/permissionset/oldap/testpermissionset', headers=header)
    res = response2.json
    print(res)
    assert res.get('comment') == None

