"""Execute placement summaries on an owned in-memory Jena server; never use live data.

Set PLACEMENT_TEST_JENA_JAR and optionally PLACEMENT_TEST_JAVA to enable.
"""
import os
from pathlib import Path
import socket
import subprocess
import time
from types import SimpleNamespace

import pytest
import requests
from oldaplib.src.helpers.context import Context
from oldaplib.src.xsd.iri import Iri
from oldap_api.archive_placement import placement_status_query


@pytest.fixture
def endpoint(tmp_path):
    jar = os.environ.get("PLACEMENT_TEST_JENA_JAR")
    if not jar:
        pytest.skip("Set PLACEMENT_TEST_JENA_JAR for isolated Jena acceptance")
    assert Path(jar).is_file()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/placement"
    with (tmp_path / "jena.log").open("w") as log:
        process = subprocess.Popen([os.environ.get("PLACEMENT_TEST_JAVA", "java"),
            "-Xmx256m", "-jar", jar, "--localhost", f"--port={port}",
            "--mem", "--update", "/placement"], cwd=tmp_path, stdout=log, stderr=log,
            env={**os.environ, "FUSEKI_BASE": str(tmp_path / "server")})
        try:
            for _ in range(100):
                assert process.poll() is None, "Owned Jena exited"
                try:
                    if requests.get(url + "/query", params={"query": "ASK {}"}, timeout=1).ok:
                        break
                except requests.ConnectionError:
                    pass
                time.sleep(.1)
            else:
                pytest.fail("Owned Jena did not start")
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def test_real_jena_counts_permissions_inheritance_and_hidden_placements(endpoint):
    context = Context(name="PLACEMENT_JENA_TEST")
    context["museum"] = "https://museum.example/"
    policy = SimpleNamespace(context=context,
        connection=SimpleNamespace(userIri=Iri("urn:test:actor"), _resource_permissions_rdf12=True),
        project=SimpleNamespace(projectShortName="museum"),
        media_classes=("https://museum.example/Media",),
        publication={"rootClassIris": ["https://museum.example/Object"],
                     "mediaToRootPropertyIri": "https://museum.example/represents"})
    data = '''GRAPH museum:onto {
      museum:Event rdfs:subClassOf museum:Object .
      museum:Image rdfs:subClassOf museum:Media .
      museum:Folder rdfs:subClassOf shared:ArchiveUnit .
    }
    GRAPH museum:data {
      museum:event a museum:Event . museum:empty a museum:Object . museum:album a museum:Object .
      museum:free a museum:Image ; museum:represents museum:event .
      museum:placed a museum:Media ; museum:represents museum:event .
      museum:restricted a museum:Media ; museum:represents museum:event .
      museum:orphan a museum:Media ; museum:represents museum:event .
      museum:hiddenFolder a museum:Folder ; shared:hasMediaObject museum:placed .
    }
    GRAPH oldap:admin {
      <urn:test:actor> oldap:hasRole museum:reader .
      oldap:DATA_VIEW oldap:permissionValue 2 .
      oldap:DATA_RESTRICTED oldap:permissionValue 1 .
    }'''
    for name in ("event", "empty", "album", "free", "placed", "restricted", "orphan"):
        permission = "DATA_RESTRICTED" if name == "restricted" else "DATA_VIEW"
        membership = f"museum:{name} oldap:attachedToRole museum:reader ." if name != "orphan" else ""
        data += f'''GRAPH museum:data {{ {membership}
          museum:grant_{name} rdf:reifies <<( museum:{name} oldap:attachedToRole museum:reader )>> ;
            oldap:hasDataPermission oldap:{permission} . }}'''
    # Album-sized batches and duplicate grants must not multiply either count.
    for index in range(255):
        data += f"""GRAPH museum:data {{
          museum:page{index} a museum:Image ; museum:represents museum:album ;
            oldap:attachedToRole museum:reader .
          museum:pageGrant{index} rdf:reifies <<( museum:page{index} oldap:attachedToRole museum:reader )>> ;
            oldap:hasDataPermission oldap:DATA_VIEW .
          museum:duplicateGrant{index} rdf:reifies <<( museum:page{index} oldap:attachedToRole museum:reader )>> ;
            oldap:hasDataPermission oldap:DATA_VIEW .
        }}"""
    response = requests.post(endpoint + "/update", data={"update": context.sparql_context + "INSERT DATA {" + data + "}"}, timeout=10)
    response.raise_for_status()

    def counts(targets):
        query = placement_status_query(policy, [{"iri": "museum:" + name, "kind": kind} for name, kind in targets])
        response = requests.post(endpoint + "/query", data={"query": query}, headers={"Accept": "application/sparql-results+json"}, timeout=10)
        response.raise_for_status()
        return {row["key"]["value"]: (int(row["total"]["value"]), int(row["unassigned"]["value"]))
                for row in response.json()["results"]["bindings"]}

    assert counts([("event", "entry"), ("empty", "entry")]) == {"museum:event": (2, 1), "museum:empty": (0, 0)}
    assert counts([("free", "media"), ("placed", "media"), ("restricted", "media"), ("orphan", "media")]) == {
        "museum:free": (1, 1), "museum:placed": (1, 0)}
    assert counts([("event", "entry"), ("free", "media")]) == {"museum:event": (2, 1), "museum:free": (1, 1)}

    assert counts([("album", "entry"), ("event", "entry"), ("placed", "media")]) == {
        "museum:album": (255, 255), "museum:event": (2, 1), "museum:placed": (1, 0)}
