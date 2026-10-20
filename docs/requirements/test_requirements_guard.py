"""Tests the traceability tool, NOT the KGnote application or learning claims."""
import copy
import tempfile
import unittest
from pathlib import Path
import requirements_guard as g

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.ledger=g.load(g.ROOT/'requirements.json')
        self.sources=g.load(g.ROOT/'sources.json')
        self.cases=g.load(g.ROOT/'scenarios.json')
    def check(self):
        return g.inspect(self.ledger,self.sources,self.cases)[0]
    def test_valid_pack_is_only_structural_pass(self):
        self.assertEqual(self.check(),[])
        self.assertTrue(any(c['run_status']=='not_run' for c in self.cases['scenarios']))
        self.assertTrue(any(c['run_status']=='automated_pass' for c in self.cases['scenarios']))
    def test_duplicate_id_rejected(self):
        self.ledger['requirements'].append(copy.deepcopy(self.ledger['requirements'][0]))
        self.assertTrue(any('duplicate requirement' in e for e in self.check()))
    def test_dangling_source_rejected(self):
        self.ledger['requirements'][0]['source_refs']=['MISSING']
        self.assertTrue(any('dangling source_refs' in e for e in self.check()))
    def test_dangling_scenario_rejected(self):
        self.ledger['requirements'][0]['scenario_ids']=['MISSING']
        self.assertTrue(any('dangling scenario_ids' in e for e in self.check()))
    def test_negative_acceptance_required(self):
        del self.ledger['requirements'][0]['acceptance']['negative']
        self.assertTrue(any('positive AND negative' in e for e in self.check()))
    def test_sections_must_be_dispositioned(self):
        self.ledger['source_section_disposition'].pop()
        self.assertTrue(any('01–27' in e for e in self.check()))
    def test_verified_claim_requires_refs(self):
        self.ledger['requirements'][0]['delivery']['status']='automated_verified'
        self.assertTrue(any('verification claimed' in e for e in self.check()))
    def test_scenario_run_without_binding_rejected(self):
        self.cases['scenarios'][0]['run_status']='automated_pass'
        self.cases['scenarios'][0]['test_binding']=None
        self.assertTrue(any('execution claimed without binding' in e for e in self.check()))
    def test_unknown_run_status_and_incomplete_binding_rejected(self):
        case=self.cases['scenarios'][0]
        case['run_status']='passed'
        case['test_binding']={'test_refs':[],'evidence_refs':[]}
        errors=self.check()
        self.assertTrue(any('unsupported run_status' in e for e in errors))
        self.assertTrue(any('non-empty test_refs' in e for e in errors))
    def test_semantic_weakening_reported(self):
        candidate=copy.deepcopy(self.ledger)
        candidate['requirements'][0]['obligation']='請先寫筆記'
        changes=g.compare(self.ledger,candidate)
        self.assertEqual(changes[0]['kind'],'semantic_fields_changed')
        self.assertFalse(changes[0]['revision_increased'])
    def test_deletion_reported(self):
        candidate=copy.deepcopy(self.ledger)
        candidate['requirements'].pop()
        self.assertEqual(g.compare(self.ledger,candidate)[0]['kind'],'removed_requirement')
    def test_packet_includes_global_constraints(self):
        p=g.packet(self.ledger,self.sources,self.cases,['context'],[])
        self.assertIn('KG-CTX-02',p)
        self.assertIn('KG-WF-01',p)
        self.assertNotIn('### KG-SRS-02',p)
    def test_no_original_hash_silent_rebase(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.md';p.write_text('not the original',encoding='utf8')
            errors,_=g.inspect(self.ledger,self.sources,self.cases,original=p)
            self.assertTrue(any('checksum mismatch' in e for e in errors))
    def test_scenario_weakening_reported(self):
        candidate=copy.deepcopy(self.cases)
        candidate['scenarios'][0]['must_fail_if']='nothing'
        changes=g.compare_catalog(self.cases,candidate,'scenarios',('must_fail_if',))
        self.assertEqual(changes[0]['kind'],'scenarios_content_changed')
    def test_packet_hash_changes_when_scenario_changes(self):
        before=g.packet(self.ledger,self.sources,self.cases,['context'],[]).splitlines()[3]
        self.cases['scenarios'][0]['must_fail_if']='changed'
        after=g.packet(self.ledger,self.sources,self.cases,['context'],[]).splitlines()[3]
        self.assertNotEqual(before,after)
    def test_render_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            g.render(root,self.ledger,self.sources,self.cases)
            before={p.name:p.read_bytes() for p in root.iterdir()}
            g.render(root,self.ledger,self.sources,self.cases)
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
            self.assertFalse(before['REQUIREMENTS_TRACE.md'].endswith(b'\n\n'))

if __name__=='__main__': unittest.main()
