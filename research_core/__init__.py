# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Small shared contracts; existing ESAE APIs/algorithms remain unchanged."""
from esae.models import now
from esae.ai import validate_ollama

EVIDENCE_KINDS=('observed_data','computational_result','ai_hypothesis','not_determinable')

def evidence(kind,description,references):
    if kind not in EVIDENCE_KINDS:raise ValueError('Unknown evidence kind')
    if not isinstance(references,list) or not references:raise ValueError('Evidence references required')
    return {'kind':kind,'description':str(description),'references':references}

class EmbeddedAdapter:
    """Opt-in adapter over an existing Engine; no original API changes."""
    name='embedded'
    def __init__(self,engine):self.engine=engine
    def list_jobs(self):return self.engine.store.list()
    def result(self,job_id):
        value=self.engine.store.get(job_id)
        return None if value is None else {'engine':self.name,'job_id':job_id,'status':value['status'],'evidence_kind':'computational_result','result':value}
