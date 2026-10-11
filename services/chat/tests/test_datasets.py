"""Módulo 2 — Motor de Datos."""
import io
import json

from .base import AuthenticatedTestCase, csv_file


class CsvUploadAndAnalysisTests(AuthenticatedTestCase):
    def test_upload_csv_creates_dataset_and_triggers_analysis(self):
        res = self.client.post(
            "/datasets",
            {"file": csv_file("precio,cantidad\n10.5,3\n20.0,1\n15.25,7\n", "ventas.csv")},
            **self.auth,
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual(body["file_type"], "csv")
        self.assertIn("id", body)

    def test_duplicate_file_is_detected_by_hash(self):
        content = "a,b\n1,2\n3,4\n"
        res1 = self.client.post("/datasets", {"file": csv_file(content, "d1.csv")}, **self.auth)
        self.assertEqual(res1.status_code, 201)
        # Mismo contenido, mismo nombre de archivo incluso distinto:
        # la deduplicación es por hash de contenido, no por nombre.
        res2 = self.client.post("/datasets", {"file": csv_file(content, "d1_copia.csv")}, **self.auth)
        self.assertIn(res2.status_code, (200, 409))


class JsonUploadTests(AuthenticatedTestCase):
    """
    Antes de la corrección documentada en el roadmap, cualquier .json se
    intentaba leer como CSV y fallaba o producía basura. Estos tests
    cubren los formatos de JSON que ahora sí se convierten correctamente.
    """

    def _upload_json(self, payload, name="data.json"):
        f = io.BytesIO(json.dumps(payload).encode("utf-8"))
        f.name = name
        return self.client.post("/datasets", {"file": f}, **self.auth)

    def test_json_list_of_objects(self):
        res = self._upload_json([{"col": 1}, {"col": 2}, {"col": 3}])
        self.assertEqual(res.status_code, 201, res.content)

    def test_json_container_with_data_key(self):
        res = self._upload_json({"data": [{"col": 1}, {"col": 2}]})
        self.assertEqual(res.status_code, 201, res.content)

    def test_json_single_object(self):
        res = self._upload_json({"col_a": 1, "col_b": 2})
        self.assertEqual(res.status_code, 201, res.content)


class ChunkedUploadTests(AuthenticatedTestCase):
    def test_file_assembled_from_sequential_chunks(self):
        header = "id,name,value\n"
        body = header + "".join(f"{i},item_{i},{i * 1.5}\n" for i in range(2000))
        data_bytes = body.encode("utf-8")

        chunk_size = len(data_bytes) // 3 + 1
        chunks = [data_bytes[i : i + chunk_size] for i in range(0, len(data_bytes), chunk_size)]
        upload_id = "test-chunk-upload-01"

        last_res = None
        for idx, chunk in enumerate(chunks):
            f = io.BytesIO(chunk)
            f.name = "chunk.part"
            last_res = self.client.post(
                "/datasets/upload-chunk/",
                {
                    "upload_id": upload_id,
                    "file_name": "archivo_grande.csv",
                    "chunk_index": str(idx),
                    "total_chunks": str(len(chunks)),
                    "chunk": f,
                },
                **self.auth,
            )

        self.assertEqual(last_res.status_code, 201, last_res.content)

        # El directorio temporal de ensamblado debe limpiarse tras el
        # último chunk, falle o no — si queda basura ahí, un upload_id
        # reusado (o un fallo a mitad de camino) deja archivos huérfanos.
        from django.conf import settings

        upload_dir = settings.MEDIA_ROOT / "chunk_uploads" / str(self.user.id) / upload_id
        self.assertFalse(upload_dir.exists())


class DatasetMergeTests(AuthenticatedTestCase):
    def test_merge_two_datasets(self):
        r1 = self.client.post("/datasets", {"file": csv_file("a,b\n1,2\n", "m1.csv")}, **self.auth)
        r2 = self.client.post("/datasets", {"file": csv_file("a,b\n3,4\n", "m2.csv")}, **self.auth)
        id1, id2 = r1.json()["id"], r2.json()["id"]

        res = self.client.post(
            "/datasets/merge/",
            data=json.dumps({"dataset_ids": [id1, id2], "name": "fusionado.csv"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(res.status_code, 201, res.content)
