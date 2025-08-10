from pprint import pprint

import jwt
from flask import jsonify
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound, OldapError
from oldaplib.src.xsd.iri import Iri


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
    assert readed["givenName"] == "Kappa"


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
    assert readed["familyName"] == "Kappa"

def test_modify_email(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "email": "manuel.rosenthaler@stud.unibas.ch"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    assert res["message"] == "User updated successfully"

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["email"] == "manuel.rosenthaler@stud.unibas.ch"


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


def test_modify_inproject_a(client, token_headers, testuser):
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
    pprint(readed)
    assert sorted(readed["inProjects"][1]["permissions"]) == sorted(['oldap:ADMIN_RESOURCES'])

def test_modify_inproject_b(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": {"add": ["ADMIN_RESOURCES"]}
            }
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert sorted(readed["inProjects"][1]["permissions"]) == sorted(['oldap:ADMIN_USERS', 'oldap:ADMIN_RESOURCES'])

def test_modify_inproject_c(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "oldap:HyperHamlet",
                "permissions": []
            }
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    tmp = [x for x in readed["inProjects"] if x['project'] == "oldap:HyperHamlet"]
    assert len(tmp) == 1

def test_modify_inproject_d(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": {"del": ["ADMIN_USERS"]}
            }
        ]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["inProjects"][1]["permissions"] == []

def test_modify_inproject_e(client, token_headers, testuser):
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
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["inProjects"][1]["permissions"] == []

def test_modify_inproject_f(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": 1234
            }
        ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "Either a list or a dict is expected for the content of the permissions field"

def test_modify_inproject_g(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": {"del": ["oldap:HyperHamlet"]},
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    for p in readed["inProjects"]:
        assert p['project'] != "oldap:HyperHamlet"

def test_modify_inproject_g(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": {"del": ["oldap:HyperHamlet"]},
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    for p in readed["inProjects"]:
        assert p['project'] != "oldap:HyperHamlet"

def test_modify_inproject_h(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": {"add": [{"project": 'oldap:SystemProject', "permissions": None}]},
    }, headers=header)
    assert response.status_code == 200
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    ishere = False
    for p in readed["inProjects"]:
        if p['project'] == "oldap:SystemProject":
            ishere = True
    assert ishere

def test_modify_inproject_i(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": {"add": [{"project": 'oldap:SystemProject', "permissions": ["ADMIN_USERS", "ADMIN_MODEL"]}]},
    }, headers=header)
    assert response.status_code == 200
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    ishere = False
    for p in readed["inProjects"]:
        if p['project'] == "oldap:SystemProject":
            assert sorted(p["permissions"]) == sorted(["oldap:ADMIN_USERS", "oldap:ADMIN_MODEL"])
            ishere = True
    assert ishere

def test_modify_bad_inproject_a(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": {"add": "ADMIN_RESOURCES"}
            }
        ]
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The add entry needs to be a list, not a string."

def test_modify_bad_inproject_b(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ]
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The Permissions are missing for the project"

def test_modify_bad_inproject_c(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "kappa1234",
                "permissions": ["ADMIN_RESOURCES"]
            }
        ]
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == 'Invalid string for IRI: "kappa1234"'

def test_modify_bad_inproject_d(client, token_headers, testuser):
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
    print(res)
    assert res["message"] == "'oldap:KAPPA_RESOURCES' is not a valid AdminPermission"

def test_modify_bad_inproject_e(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": {"add": "KAPPA_RESOURCES"}
            }
        ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The add entry needs to be a list, not a string."

def test_modify_bad_inproject_f(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": {"del": "KAPPA_RESOURCES"}
            }
        ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The del entry needs to be a list, not a string."

def test_modify_bad_inproject_g(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": 1234
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "Either a List or a dict is expected for a modify request."

def test_modify_bad_inproject_h(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
            "inProjects": [
                {
                    "project": 1234,
                    "permissions": {"del": "KAPPA_RESOURCES"}
                }
            ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == 'Invalid value for IRI: "1234"'

def test_modify_bad_inproject_i(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
            "inProjects": [
                {
                    "project": "oldap:HyperHamlet",
                    "permissions": {"del": "KAPPA_RESOURCES"}
                }
            ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The del entry needs to be a list, not a string."

def test_modify_bad_inproject_j(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
            "inProjects": [
                {
                    "project": "oldap:HyperHamlet",
                    "permissions": {"del": ["KAPPA_RESOURCES"]}
                }
            ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "'oldap:KAPPA_RESOURCES' is not a valid AdminPermission"

def test_modify_bad_inproject_k(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
            "inProjects": [
                {
                    "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                    "permissions": {"del": ["ADMIN_LISTS"]}
                }
            ]
    }, headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == "The permission ADMIN_LISTS is not present in the database"

def test_modify_bad_inproject_l(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "kappa": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": ["ADMIN_RESOURCES"]
            }
        ]
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The project-field is missing in the request"


def test_inprojects_none(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": None
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["inProjects"] == []


def test_inprojects_permission_none(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
                "permissions": None
            }
        ]
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    pprint(readed)
    for obj in readed["inProjects"]:
        assert obj["project"] != "http://www.salsah.org/version/2.0/SwissBritNet"
    #assert readed["inProjects"].get(Iri("http://www.salsah.org/version/2.0/SwissBritNet")) == None
    #assert sorted(readed["inProjects"][1]["permissions"]) == sorted([])


def test_modify_empty_permissions_inprojects(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": [
            {
                "project": "http://www.salsah.org/version/2.0/SwissBritNet",
            }
        ]
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)


def test_modify_empty_inproject(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "inProjects": []
    }, headers=header)

    res = response.json
    assert response.status_code == 400


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
    print(res)

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    print(readed)
    assert readed["inProjects"][1]["permissions"] == []


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
    print(res)


def test_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": [
            "GenericRestricted",
            "GenericView"
        ]
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert sorted(readed["hasPermissions"]) == sorted(['oldap:GenericRestricted', 'oldap:GenericView'])

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": {"del": ["GenericRestricted", "GenericView"]}
    }, headers=header)
    assert response.status_code == 200
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["hasPermissions"] == []

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": {"del": ["GenericRestricted"]}
    }, headers=header)
    assert response.status_code == 404

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": None
    }, headers=header)
    assert response.status_code == 200
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["hasPermissions"] == []


def test_modify_empty_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": []
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["hasPermissions"] == []


def test_notwellformed_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": ['Gagaga+++kappa']
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "The given permission is not a QName"

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": 'Gagaga+++kappa'
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    assert res["message"] == "For the permissionset either a list or a dict is expected, not a string"


def test_bad_modify_haspermission(client, token_headers, testuser):
    header = token_headers[1]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": ['Gagagakappa']
    }, headers=header)

    assert response.status_code == 404
    res = response.json
    print(res)
    assert res["message"] == "One of the permission sets is not existing!"

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": {"add": "abcd"}
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": {"add": ["GenericRestricted"]}
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert sorted(readed["hasPermissions"]) == sorted(["oldap:GenericRestricted", "oldap:GenericView"])

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": {"add": ["GenericRestricted"], "del": ["GenericView"]}
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)
    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed["hasPermissions"] == ["oldap:GenericRestricted"]

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": {"del": "GenericRestricted"}
    }, headers=header)

    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "The delete entry needs to be a list, not a string."

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": {"kappa": "GenericRestricted"}
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    assert res["message"] == "The sended command (keyword in dict) is not known"

    response = client.post('/admin/user/rosman', json={
        "hasPermissions": 1234
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)
    assert res["message"] == "Either a List or a dict is required."


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
    assert readed["givenName"] == "Kappa kappa"


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
    assert readed["givenName"] == "LoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisatveroerosetaccumsanetiustoodiodignissimquiblanditpraesentluptatumzzrildelenitaugueduisdoloretefeugaitnullafacilisiLoremipsumdolorsitametconsectetueradipiscingelitseddiamnonummynibheuismodtinciduntutlaoreetdoloremagnaaliquameratvolutpatUtwisienimadminimveniamquisnostrudexercitationullamcorpersuscipitlobortisnislutaliquipexeacommodoconsequatDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisatveroerosetaccumsanetiustoodiodignissimquiblanditpraesentluptatumzzrildelenitaugueduisdoloretefeugaitnullafacilisiNamlibertemporcumsolutanobiseleifendoptionconguenihilimperdietdomingidquodmazimplaceratfacerpossimassumLoremipsumdolorsitametconsectetueradipiscingelitseddiamnonummynibheuismodtinciduntutlaoreetdoloremagnaaliquameratvolutpatUtwisienimadminimveniamquisnostrudexercitationullamcorpersuscipitlobortisnislutaliquipexeacommodoconsequatDuisautemveleumiriuredolorinhendreritinvulputatevelitessemolestieconsequatvelillumdoloreeufeugiatnullafacilisisAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrAtaccusamaliquConsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdoloremagnaaliquyameratseddiamvoluptuaAtveroeosetaccusametjustoduodoloresetearebumStetclitakasdgubergrennoseatakimatasanctusestLoremipsumdolorsitametLoremipsumdolorsitametconsetetursadipscingelitrseddiamnonumyeirmodtemporinviduntutlaboreetdolore"


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
        "email": "kappa.user@kappa.com",
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
        "isActive": False
    }, headers=header)

    assert response.status_code == 200
    res = response.json

    read = client.get('/admin/user/rosman', headers=header)
    readed = read.json
    assert readed['isActive'] is False

    response2 = client.post('/admin/user/rosman', json={
        "isActive": "TRUE"
    }, headers=header)
    assert response2.status_code == 400
    read2 = client.get('/admin/user/rosman', headers=header)
    readed2 = read2.json
    assert readed2['isActive'] is False


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
        "email": "manuel.rosenthaler@unibas.ch",
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
