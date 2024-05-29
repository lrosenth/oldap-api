from pprint import pprint

import jwt
from flask import jsonify
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapError


def test_modify_givenname(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "givenName": "Kappa"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["given_name"] == "Kappa"


def test_modify_familyname(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "familyName": "Kappa"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["family_name"] == "Kappa"


def test_modify_credentials(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "password": "Kappa"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    # Wenn Connection funktioniert dann update erfolgreich.
    con = Connection(server='http://localhost:7200',
                     repo="oldap",
                     userId="rosman",
                     credentials="Kappa",
                     context_name="DEFAULT")


def test_modify_inproject(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": ["ADMIN_RESOURCES"]
            }
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json


def test_modify_bad_inproject(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": ["KAPPA_RESOURCES"]
            }
        ]
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "The given project permission is not a valid one"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)


def test_modify_empty_permissions_inprojects(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)


def test_modify_empty_inproject(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": []
    }, headers=header)

    res = response.json
    assert response.status_code == 200

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["in_projects"] == []


def test_modify_empty_inproject_permissions(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": []
            }
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["in_projects"][0]["permissions"] == []


def test_modify_empty_inproject_name(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "",
                "permissions": ["ADMIN_RESOURCES"]
            }
        ]
    }, headers=header)

    assert response.status_code == 400
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["in_projects"][0]["permissions"] == ["oldap:ADMIN_USERS"]
    assert readed["in_projects"][0]["project"] == "http://www.salsah.org/version/2.0/SwissBritNet"


def test_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": [
            "GenericView"
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["has_permissions"] == ['oldap:GenericView']


def test_modify_empty_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": []
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["has_permissions"] == []


def test_notwellformed_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": ['Gagaga+++kappa']
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "The given permission is not a QName"


def test_bad_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": ['Gagagakappa']
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == "One of the permission sets is not existing!"


def test_malicious_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": ['Gagaga+++kappa<!$']
    }, headers=header)

    assert response.status_code == 400


def test_bad_general_modify_request(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={'random shit': 'kappa'}, headers=header)

    res = response.json
    assert response.status_code == 400


def test_blanks_in_modify(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "givenName": "Kappa kappa"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["given_name"] == "Kappa kappa"


def test_too_long_modify(client, token_headers, testuser):
    # TODO: Macht es wirklich sinn so lange Strings zuzulassen?
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "givenName": "LoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisatveroerosetaccumsanetiustoodiodignissimquiblanditpraesentluptatumzzrildelenitaugueduisdoloretefeugaitnullafacilisiLoremipsumdolorsitametconsectetueradipiscingelitseddiamnonummynibheuismodtinciduntutlaoreetdoloremagnaaliquameratvolutpatUtwisienimadminimveniamquisnostrudexercitationullamcorpersuscipitlobortisnislutaliquipexeacommodoconsequatDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisatveroerosetaccumsanetiustoodiodignissimquiblanditpraesentluptatumzzrildelenitaugueduisdoloretefeugaitnullafacilisiNamlibertemporcumsolutanobiseleifendoptionconguenihilimperdietdomingidquodmazimplaceratfacerpossimassumLoremipsumdolorsitametconsectetueradipiscingelitseddiamnonummynibheuismodtinciduntutlaoreetdoloremagnaaliquameratvolutpatUtwisienimadminimveniamquisnostrudexercitationullamcorpersuscipitlobortisnislutaliquipexeacommodoconsequatDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrAtaccusamaliquConsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdolore"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["given_name"] == "LoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisatveroerosetaccumsanetiustoodiodignissimquiblanditpraesentluptatumzzrildelenitaugueduisdoloretefeugaitnullafacilisiLoremipsumdolorsitametconsectetueradipiscingelitseddiamnonummynibheuismodtinciduntutlaoreetdoloremagnaaliquameratvolutpatUtwisienimadminimveniamquisnostrudexercitationullamcorpersuscipitlobortisnislutaliquipexeacommodoconsequatDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisatveroerosetaccumsanetiustoodiodignissimquiblanditpraesentluptatumzzrildelenitaugueduisdoloretefeugaitnullafacilisiNamlibertemporcumsolutanobiseleifendoptionconguenihilimperdietdomingidquodmazimplaceratfacerpossimassumLoremipsumdolorsitametconsectetueradipiscingelitseddiamnonummynibheuismodtinciduntutlaoreetdoloremagnaaliquameratvolutpatUtwisienimadminimveniamquisnostrudexercitationullamcorpersuscipitlobortisnislutaliquipexeacommodoconsequatDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrAtaccusamaliquConsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdolore"


def test_no_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/user/rosman', 'Kein JSON!!', headers=header)
    assert response.status_code == 400
    res = response.json
    assert 'message' in res
    assert res['message'] == "JSON expected. Instead received None"


def test_empty_json(client, token_headers, testuser):
    header = token_headers[1]
    response = client.post('/admin/user/rosman', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_nonexisting_user(client, token_headers):
    header = token_headers[1]

    response = client.post('/admin/user/nonexistinguser', json={
        "givenName": "Kappa"
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    assert res['message'] == 'User "nonexistinguser" not found.'


def test_bad_token(client, token_headers):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/user/nonexistinguser', json={
        "givenName": "Kappa"
    }, headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"


def test_no_permission_modify(client, token_headers, testuser):
    header = token_headers[1]

    client.put('/admin/user/rosmankappa', json={
        "givenName": "Kappauser",
        "familyName": "KappaKappatest",
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

    response2 = client.post('/admin/user/rosman', json={
        "givenName": "Kappa"
    }, headers=headers)
    assert response2.status_code == 403


def test_modify_active(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "isActive": "false"
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed['isActive'] == 'false'

    response2 = client.post('/admin/user/rosman', json={
        "isActive": "TRUE"
    }, headers=header)
    read2 = client.get('/admin/user/rosman', headers=header)
    readed2 = read2.json
    assert readed2['isActive'] == 'true'

    response3 = client.post('/admin/user/rosman', json={
        "givenName": "Kappa"
    }, headers=header)
    read3 = client.get('/admin/user/rosman', headers=header)
    readed3 = read3.json
    print(readed3)
    assert readed3['isActive'] == 'true'


def test_modify_nonsense(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={}, headers=header)

    # assert response.status_code == 200
    res = response.json
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)


def test_json_with_unknown_fields(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "kappa": "Kappa"
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_change_own_user_pw(client, token_headers):
    header = token_headers[1]

    #
    # Create a new user
    #
    response = client.put('/admin/user/rosman', json={
        "givenName": "Manuel",
        "familyName": "Rosenthaler",
        "password": "kappa1234",
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": [
                    "ADMIN_USERS"
                ]
            }
        ],
        "hasPermissions": [
            "GenericView"
        ]
    }, headers=header)

    #
    # Login with the new user
    #
    response2 = client.post('/admin/auth/rosman', json={'password': 'kappa1234'})
    res = response2.json
    assert res["message"] == "Login succeeded"
    usertoken = res["token"]

    #
    # Change the password of "myself"
    #
    headerss = {
        'Authorization': f'Bearer {usertoken}'
    }
    response3 = client.post('/admin/user/rosman', json={
        "password": "gaga"
    }, headers=headerss)
    res3 = response3.json

    #
    # Login with the new password
    #
    response4 = client.post('/admin/auth/rosman', json={'password': 'gaga'})
    res4 = response4.json
    assert res4["message"] == "Login succeeded"
