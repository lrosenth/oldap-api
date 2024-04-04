
def test_create_project(client, token_headers):
    header = token_headers[1]

    response = client.post('/admin/project/testproject', json={
        "projectIri": "string",
        "label": ["unittest@en", "unittest@de"],
        "comment": ["For testing@en", "Für Tests@de"],
        "namespaceIri": "http://unitest.org/project/unittest#",
        "projectStart": "1993-04-05",
        "projectEnd": "2000-01-10"
    }, headers=header)

    assert response.status_code == 200
    res = response.json
    print(res)

