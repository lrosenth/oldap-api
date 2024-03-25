import jwt
from flask import jsonify
from omaslib.src.connection import Connection
from omaslib.src.helpers.omaserror import OmasErrorNotFound, OmasError


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


def test_bad_modify_givenname(client, token_headers, testuser):
    # TODO: Dieser Test muss noch im Backend abgefangen werden
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "givenName": "gagagag<!$"  # TODO: Werden hier Sonderzeichen nicht rausgenommen?
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    # assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["given_name"] == ""


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
                     repo="omas",
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
    assert readed["in_projects"][0]["permissions"] == ["omas:ADMIN_USERS"]
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
    assert readed["has_permissions"] == ['omas:GenericView']


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


def test_bad_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": ['Gagaga+++kappa']
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "The given permission is not a QName"


def test_malicious_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": ['Gagaga+++kappa<!$'] # TODO: wenn man Gagaga+++kappa<!$ eingibt dann kommt komischer error. Injection?
    }, headers=header)

    assert response.status_code == 400


def test_bad_general_modify_request(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={'random shit': 'kappa'}, headers=header)

    res = response.json
    assert response.status_code == 400
    assert res["message"] == "Either the firstname, lastname, password, inProjects or hasPermissions needs to be modified"


def test_blanks_in_modify(client, token_headers, testuser):
    # TODO: Should blanks be allowed in Names?
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

