from pprint import pprint

from oldaplib.src.xsd.iri import Iri


def test_modify_standaloneprop_langstring(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["kappa@de"],
        "description": ["gigakappa@de"],
        "languageIn": {'add': ['zu'], 'del': ['fr', 'it']},
        "uniqueLang": True,
        "minLength": 2,
        "maxLength": 51,
        "pattern": r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$",
        "minExclusive": 5.6,
        "minInclusive": 5.6,
        "maxExclusive": 5.6,
        "maxInclusive": 5.6,
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert ele["name"] == ["kappa@de"]
        assert ele["description"] == ["gigakappa@de"]
        assert set(ele["languageIn"]) == set(["en", "de", "zu"])
        assert ele["uniqueLang"] == True
        assert ele["minLength"] == 2
        assert ele["maxLength"] == 51
        assert ele["pattern"] == r"^[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
        assert ele["minExclusive"] == 5.6
        assert ele["minInclusive"] == 5.6
        assert ele["maxExclusive"] == 5.6
        assert ele["maxInclusive"] == 5.6

def test_modify_standaloneprop_langstring_01(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": ["en", "de"],
    }, headers=header)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert set(ele["languageIn"]) == set(["en", "de", ])

def test_modify_standaloneprop_langstring_02(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@en"], "del": ["Kappa@de"]},
    }, headers=header)
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        print(ele["name"])
        assert ele["name"] == ["NewKappa@en"]

def test_modify_standaloneprop_langstring_03(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]
    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "iri": ["kappa:kappashit"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring_04(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["kappa@z"],
    }, headers=header)
    res = response.json
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert ele["name"] == ["kappa@z@en"]

def test_modify_standaloneprop_langstring_05(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["kappa@zz"],
    }, headers=header)
    res = response.json
    assert response.status_code == 400

def test_modify_standaloneprop_langstring_06(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["z"],
    }, headers=header)
    res = response.json
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert ele["name"] == ["z@en"]

def test_modify_standaloneprop_langstring_07(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa"], "del": ["Kappa"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

def test_modify_standaloneprop_langstring_08(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["a"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 200

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert set(ele["name"]) == {"a@en", "Test Feld@de"}

def test_modify_standaloneprop_langstringG(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["@en"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert "name" not in ele

def test_modify_standaloneprop_langstringH(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["Kappa"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

def test_modify_standaloneprop_langstringI(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@zz"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

def test_modify_standaloneprop_langstringJ(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@gaga"], "del": ["Kappa@gaga"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

def test_modify_standaloneprop_langstringK(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["Kappa@gaga"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

def test_modify_standaloneprop_langstringL(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["Kappa@zz"]},
    }, headers=header)
    res = response.json
    assert response.status_code == 400

def test_modify_standaloneprop_langstringD(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert "name" not in ele

def test_modify_standaloneprop_langstringE(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": "gaga",
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringF(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        None: "gaga",
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringG(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={}, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringH(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    for item in res["standaloneProperties"]:
        if item["iri"] == "hyha:testProp2":
            assert "languageIn" not in item

def test_modify_standaloneprop_langstringI(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "minLength": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert "minLength" not in ele

def test_modify_standaloneprop_langstringJ(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringK(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": "gaga", "kappa": "gigi"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringL(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": "gaga", "del": "gigakappa", "kappa": "gigi"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringM(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringN(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": "kappa"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringO(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringP(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringQ(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": "kappa"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringR(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringS(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringT(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": "kappa"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringU(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringV(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringW(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"add": ["kappa"], "doesnotexist": ["kappa2"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringX(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringY(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstringZ(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring01(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring02(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring03(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring04(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring05(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["kappa"], "doesnotexist": ["kappa2"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring06(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring07(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring08(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring09(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring10(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": "kappa@en"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring11(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"add": "kappa@en"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring12(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"del": "kappa@en"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring13(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": "kappa@en"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring14(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": "kappa@en"},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring15(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["doesnotexist@af"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring16(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "inSet": {"del": ["doesnotexist"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 404

def test_modify_standaloneprop_langstring16(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": ["kappa"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_standaloneprop_langstring17(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"add": ["en", "en"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert sorted(ele["languageIn"]) == sorted(['de', 'en', 'fr', 'it'])

def test_modify_standaloneprop_langstring18(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": {"del": ["zh"]},
    }, headers=header)
    res = response.json
    print(res)
    # assert response.status_code == 400
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    pprint(res)


def test_modify_standaloneprop_string(client, token_headers, testfulldatamodelstandalonepropstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "name": ["kappa@de"],
        "description": ["gigakappa@de"],
        # "inSet": ["gugus"],
        "inSet": {"add": ["gigi"], "del": ["gugus", "Gaga"]},
        "minLength": 2,
        "maxLength": 51,
        "pattern": "kappa",
        "minExclusive": 5.6,
        "minInclusive": 5.6,
        "maxExclusive": 5.6,
        "maxInclusive": 5.6,
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue

        assert ele["name"] == ["kappa@de"]
        assert ele["description"] == ["gigakappa@de"]
        assert set(ele["inSet"]) == set(["gigi", "Kappa"])
        assert ele["minLength"] == 2
        assert ele["maxLength"] == 51
        assert ele["pattern"] == "kappa"
        assert ele["minExclusive"] == 5.6
        assert ele["minInclusive"] == 5.6
        assert ele["maxExclusive"] == 5.6
        assert ele["maxInclusive"] == 5.6

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "inSet": ["gugus"],
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert ele["inSet"] == ["gugus"]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "inSet": None,
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        assert "inSet" not in ele


def test_modify_resource_01(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "closed": False,
        #"label": ["Ein Test@de"],
        #"comment": ["A test comment@en"],
        "label": {"add": ["Ein Test@zu"], "del": ["Eine Buchseite@de"]},
        "comment": {"add": ["Ein Test@zu"], "del": ["A page of a book@en"]},
    }, headers=header)
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    assert res["resources"][0]["closed"] == False
    assert set(res["resources"][0]["label"]) == set(['A page of a book@en', "Ein Test@zu"])
    assert set(res["resources"][0]["comment"]) == set(["Eine Buchseite@de", "Ein Test@zu"])

def test_modify_resource_02(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["Edeutsch kappa@de"],
        "comment": ["english kappa@en"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    assert res["resources"][0]["label"] == ["Edeutsch kappa@de"]
    assert res["resources"][0]["comment"] == ["english kappa@en"]

def test_modify_resource_03(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["Edeutsch kappa@d"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    assert res["resources"][0]["label"] == ["Edeutsch kappa@d@en"]


def test_modify_resource_04(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["Edeutsch kappa@zz"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_05(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["Edeutsch kappa@zz"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_06(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": ["d"],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    assert res["resources"][0]["label"] == ["d@en"]


def test_modify_resource_07(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": ["Ein Test@z"], "del": ["Eine Buchseite@de"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    assert res["resources"][0]["label"] == ['Ein Test@z@en']


def test_modify_resource_08(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": ["Ein Test@z"], "del": ["Eine Buchseite@de"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    assert res["resources"][0]["label"] == ['Ein Test@z@en']

def test_modify_resource_09(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": ["Eine Buchseite@d"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_10(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": ["Ei"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 200
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    assert set(res["resources"][0]["label"]) == {'Eine Buchseite@de', 'Ei@en'}


def test_modify_resource_11(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": ["Ei"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_12(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": ["Ein Test@zz"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_13(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": ["Eine Buchseite@zz"]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_14(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": "kappa",
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_15(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": None,
    }, headers=header)
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    pprint(res)
    for resource in res["resources"]:
        if resource["iri"] == "hyha:Sheep":
            assert resource.get("label") is None

def test_modify_resource_16(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": [],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_17(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_18(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_19(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"add": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_20(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": []},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_modify_resource_21(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"del": [None]},
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

def test_bad_token_standaloneprop(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/datamodel/hyha/hyha:testProp/mod', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_bad_token_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]
    token = header['Authorization'].split(' ')[1]
    modified_token = token + "kappa"
    header['Authorization'] = 'Bearer ' + modified_token

    response = client.post('/admin/datamodel/hyha/hyha:testProp2', headers=header)
    assert response.status_code == 403
    res = response.json
    assert res["message"] == "Connection failed: Wrong credentials"

def test_cantfind_dm_to_modify(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/doesnotexist/hyha:testProp/mod', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/kappadoesnotexist/property/hyha:testProp2', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_cantfind_dm_to_modify_resource(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/doesnotexist/hyha:testProp2', headers=header)
    assert response.status_code == 404
    res = response.json
    print(res)

def test_modify_resource_add_local_property(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep/hyha:aNewProp', json={
        "datatype": "xsd:string",
        "name": ["A new property@en", "Eine neue Eigenschaft@de"],
        "maxCount": 1
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)

def test_modify_resource_add_standalone_property(client, token_headers, testfulldatamodelresourcewithstandalone):
    header = token_headers[1]

    response = client.put('/admin/datamodel/hyha/hyha:Sheep/hyha:testPropAdd', json={
        "minCount": 1,
        "maxCount": 1,
        "order": 3
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)


def test_modify_attribute_in_has_prop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    for ele in res["resources"]:
        if Iri(ele["iri"]).prefix != "hyha:sheep":
            continue
        assert ele["maxCount"] == 4
        assert ele["minCount"] == 2
        assert ele["order"] == 42
        for item in ele["hasProperty"]:
            if item["property"]["iri"] == "hyha:testProp2":
                assert item["property"]["name"] == "pappakappa@de"
                assert set(item["property"]["languageIn"]) == set["zu", "en", "it", "de"]
        assert "inSet" not in ele

def test_unknown_json_fields_for_property_modifier(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "Doesnotexist": "kappa1234",
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_unknown_json_fields_for_property_in_property_modifier(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "doesnotexist": "kappa1234",
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {},
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={}, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_bad_fields_modify_resource(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "Doesnotexist": "kappa1234",
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={

    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": [None],
    }, headers=header)
    res = response.json
    print(res)
    assert response.status_code == 400

    response = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "label": {"gaga": "kappa"},
    }, headers=header)
    res = response.json
    print(res)


def test_bad_fields_in_modify_attribute_in_has_prop(client, token_headers, testfulldatamodelresource):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": "zu"}
        }
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

    response = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"del": "zu"}
        }
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_no_permission_to_modify_attribute_in_has_propresource(client, token_headers, testfulldatamodelresource):
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
    response2 = client.post('/admin/datamodel/hyha/hyha:Sheep/hyha:testProp2', json={
        "property": {
            "name": ["pappakappa@de"],
            "languageIn": {"add": ["zu"], "del": ["fr"]}
        },
        "maxCount": 4,
        "minCount": 2,
        "order": 42
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403


def test_no_permission_modify_standalone_prop(client, token_headers, testfulldatamodelstandaloneproplangstring):
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

    response2 = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["NewKappa@en"], "del": ["Kappa@de"]},
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403

def test_no_permission_modify_resource(client, token_headers, testfulldatamodelresource):
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

    response2 = client.post('/admin/datamodel/hyha/hyha:Sheep', json={
        "closed": False,
        #"label": ["Ein Test@de"],
        #"comment": ["A test comment@en"],
        "label": {"add": ["Ein Test@zu"], "del": ["Eine Buchseite@de"]},
        "comment": {"add": ["Ein Test@zu"], "del": ["A page of a book@en"]},
    }, headers=headers)
    res2 = response2.json
    print(res2)
    assert response2.status_code == 403

def test_stuff(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": ["kappa@de", "gaga@de"],
    }, headers=header)
    #assert response.status_code == 400
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    res = response.json
    pprint(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert sorted(ele["name"]) == sorted(["gaga@de"])

def test_double_language_set(client, token_headers, testfulldatamodelstandalonepropstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "inSet": ["kappa"],
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)

def test_no_list_or_dict(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "languageIn": 1234,
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_modify_standaloneprop_inSet_empty(client, token_headers, testfulldatamodelstandalonepropstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "inSet": ["kappa", "zwei"],
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert sorted(ele["inSet"]) == sorted(["zwei@en"])

def test_del_inset_standaloneprop_inSet_empty(client, token_headers, testfulldatamodelstandalonepropstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp3', json={
        "inSet": {"del": ["kappa", "zwei"]},
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert sorted(ele["inSet"]) == sorted(['gugus', 'Kappa', 'Gaga'])

def test_modify_standaloneprop_inSet_empty(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"add": ["kappa@zu", "zwei@zh"]},
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert sorted(ele["name"]) == sorted(['Test Property@en', 'Test Feld@de', 'kappa@zu', 'zwei@zh'])

def test_language_not_in_property(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["kappa@zu", "zwei@zh"]},
    }, headers=header)
    assert response.status_code == 400
    res = response.json
    print(res)

def test_del_with_only_lang_tag(client, token_headers, testfulldatamodelstandaloneproplangstring):
    header = token_headers[1]

    response = client.post('/admin/datamodel/hyha/property/hyha:testProp2', json={
        "name": {"del": ["@en"]},
    }, headers=header)
    assert response.status_code == 200
    res = response.json
    print(res)
    response = client.get('/admin/datamodel/hyha', headers=header)
    assert response.status_code == 200
    res = response.json
    pprint(res)
    for ele in res["standaloneProperties"]:
        if Iri(ele["iri"]).prefix != "hyha":
            continue
        pprint(ele)
        assert sorted(ele["name"]) == sorted(['Test Feld@de'])
