import io
import os
import unittest

import pandas as pd

from tests.helpers import SessionTestCase, orchestrator, strict_json

SAMPLE = (
    "date,vendor,category,amount,status\n"
    + "".join(
        f"2026-01-{(i % 28) + 1:02d},V{i % 3},{'Office' if i % 2 else 'office '},{10 + i * 7.5},paid\n"
        for i in range(40)
    )
    + "2026-02-01,V0,Travel,-120.0,paid\n"
    + "2026-02-02,V2,Meals,,\n"
)


class FullPipelineTests(SessionTestCase):
    def test_unpaid_session_is_refused(self):
        d = self.make_session("unpaid", "input.csv", SAMPLE)
        self.assertEqual(orchestrator.main(["unpaid", "--stage", "profile"]), 0)
        self.assertEqual(orchestrator.main(["unpaid", "--stage", "full"]), 1)
        self.assertFalse(os.path.exists(os.path.join(d, "final_workbook.xlsx")))
        self.assertEqual(self.session(d)["status"], "profiled")

    def test_paid_session_runs_end_to_end(self):
        d = self.make_session("paid", "input.csv", SAMPLE, paid=True)
        self.assertEqual(orchestrator.main(["paid", "--stage", "profile"]), 0)
        self.assertEqual(orchestrator.main(["paid", "--stage", "full"]), 0)
        session = self.session(d)
        self.assertEqual(session["status"], "complete")
        for name in ("profile", "analysis", "audit_trail", "decision_memo", "conflict_resolution"):
            strict_json(os.path.join(d, f"{name}.json"))
        self.assertTrue(os.path.getsize(os.path.join(d, "final_workbook.xlsx")) > 1000)
        self.assertEqual(set(session["agentSeconds"]), {"Researcher", "Analyst", "Auditor", "Manager"})
        self.assertFalse(os.path.exists(os.path.join(d, ".workflow.lock")))

    def test_full_stage_profiles_first_when_needed(self):
        d = self.make_session("direct", "input.csv", SAMPLE, paid=True)
        self.assertEqual(orchestrator.main(["direct"]), 0)
        self.assertEqual(self.session(d)["status"], "complete")

    def test_auditor_flags_but_never_changes_negatives_or_blanks(self):
        d = self.make_session("flags", "input.csv", SAMPLE, paid=True)
        orchestrator.main(["flags"])
        cleaned = pd.read_csv(os.path.join(d, "cleaned_data.csv"))
        self.assertIn(-120.0, cleaned["amount"].tolist())
        self.assertTrue(cleaned["amount"].isna().any())
        trail = strict_json(os.path.join(d, "audit_trail.json"))
        issues = {i["issue"] for i in trail["data_quality_issues"]}
        self.assertEqual(issues, {"Missing value", "Negative value"})
        for key in ("corrections", "data_quality_issues", "standardizations", "deduplications"):
            self.assertIn(key, trail)

    def test_exact_duplicates_are_removed_and_logged(self):
        content = "id,amount\n1,10\n2,20\n2,20\n3,30\n"
        d = self.make_session("dups", "input.csv", content, paid=True)
        orchestrator.main(["dups"])
        cleaned = pd.read_csv(os.path.join(d, "cleaned_data.csv"))
        self.assertEqual(cleaned["id"].tolist(), [1, 2, 3])
        trail = strict_json(os.path.join(d, "audit_trail.json"))
        self.assertEqual(trail["deduplications"][0]["rows_removed"], 1)

    def test_formula_like_text_never_becomes_a_formula(self):
        import openpyxl
        content = 'name,amount\n"=1+1",5\nok,6\n'
        d = self.make_session("formula", "input.csv", content, paid=True)
        orchestrator.main(["formula"])
        ws = openpyxl.load_workbook(os.path.join(d, "final_workbook.xlsx"))["Cleaned Data"]
        cells = [c for row in ws.iter_rows() for c in row if c.value == "=1+1"]
        self.assertTrue(cells)
        self.assertTrue(all(c.data_type == "s" for c in cells))

    def test_numbers_stay_numbers_in_the_workbook(self):
        import openpyxl
        d = self.make_session("types", "input.csv", "k,amount\na,1.5\nb,2.5\n", paid=True)
        orchestrator.main(["types"])
        ws = openpyxl.load_workbook(os.path.join(d, "final_workbook.xlsx"))["Cleaned Data"]
        values = [c.value for row in ws.iter_rows() for c in row if c.value in (1.5, 2.5)]
        self.assertEqual(sorted(values), [1.5, 2.5])

    def test_clean_dataset_still_produces_a_workbook(self):
        d = self.make_session("clean", "input.csv", "id,amount\n1,10\n2,20\n3,30\n", paid=True)
        self.assertEqual(orchestrator.main(["clean"]), 0)
        self.assertTrue(os.path.exists(os.path.join(d, "final_workbook.xlsx")))


class InputVariantTests(SessionTestCase):
    def profile(self, name, filename, content):
        d = self.make_session(name, filename, content)
        code = orchestrator.main([name, "--stage", "profile"])
        return d, code

    def test_empty_file_gives_friendly_error(self):
        d, code = self.profile("empty", "input.csv", "")
        self.assertEqual(code, 1)
        s = self.session(d)
        self.assertEqual(s["status"], "profile_error")
        self.assertIn("empty", s["detail"].lower())

    def test_header_only_file_profiles_with_warning(self):
        d, code = self.profile("hdr", "input.csv", "a,b,c\n")
        self.assertEqual(code, 0)
        self.assertTrue(any("no data rows" in w for w in strict_json(os.path.join(d, "profile.json"))["warnings"]))

    def test_latin1_csv(self):
        d, code = self.profile("latin", "input.csv", "name,amount\nCaf\xe9,5\n".encode("latin-1"))
        self.assertEqual(code, 0)

    def test_semicolon_csv(self):
        d, code = self.profile("semi", "input.csv", "a;b;c\n1;2;3\n4;5;6\n")
        self.assertEqual(strict_json(os.path.join(d, "profile.json"))["column_count"], 3)

    def test_xlsx_input(self):
        buf = io.BytesIO()
        pd.DataFrame({"x": [1, 2, 3], "y": ["a", "b", "c"]}).to_excel(buf, index=False)
        d, code = self.profile("xlsx", "input.xlsx", buf.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(d, "raw", "data.csv")))

    def test_garbage_xlsx_gives_friendly_error(self):
        d, code = self.profile("badx", "input.xlsx", b"this is not a spreadsheet")
        self.assertEqual(code, 1)
        self.assertEqual(self.session(d)["status"], "profile_error")

    def test_all_null_and_constant_columns_produce_valid_json(self):
        content = "a,b,c\n" + "".join("1,,x\n" for _ in range(30))
        d = self.make_session("nulls", "input.csv", content, paid=True)
        self.assertEqual(orchestrator.main(["nulls"]), 0)
        for name in ("profile", "analysis", "decision_memo"):
            strict_json(os.path.join(d, f"{name}.json"))

    def test_second_run_while_locked_is_a_noop(self):
        d = self.make_session("locked", "input.csv", SAMPLE, paid=True)
        with open(os.path.join(d, ".workflow.lock"), "w") as f:
            f.write(str(os.getpid()))
        self.assertEqual(orchestrator.main(["locked"]), 0)
        self.assertFalse(os.path.exists(os.path.join(d, "final_workbook.xlsx")))


if __name__ == "__main__":
    unittest.main()
