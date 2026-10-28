"""Opt-in numeric OCR rejects ambiguity while preserving all Maa-filtered candidates."""
from types import SimpleNamespace
import numpy as np
import pytest
from driver_epic_seven.vision import Vision


@pytest.mark.parametrize('texts,score,expected,ambiguous', [(['0'],.99,True,False),(['0','40'],.99,False,True),(['0'],.97,False,False),([],1,False,False)])
def test_unique_ocr_keeps_candidates_and_refuses_ambiguity(texts,score,expected,ambiguous):
    v=Vision.__new__(Vision);v.templates={}
    v.spec={'templates':{},'states':{},'ocr':{'number':{'node':'Number','expected':r'\d+','min_score':.98,'require_unique':True}}}
    rows=[SimpleNamespace(text=t,score=score,box=[0,0,1,1]) for t in texts]
    a=v.inspect(np.zeros((1,1,3),dtype=np.uint8),lambda name:SimpleNamespace(filtered_results=rows))
    m=a['matches']['number'];assert m['hit'] is expected and m['ambiguous'] is ambiguous
    assert [r['text'] for r in m['filtered_candidates']]==texts
    assert m['text']==(texts[0] if expected else None)


def test_existing_ocr_without_uniqueness_flag_keeps_its_behavior():
    v=Vision.__new__(Vision);v.templates={}
    v.spec={'templates':{},'states':{},'ocr':{'number':{'node':'Number','expected':r'\d+','min_score':.98}}}
    rows=[SimpleNamespace(text=t,score=.99,box=[0,0,1,1]) for t in ('0','40')]
    m=v.inspect(np.zeros((1,1,3),dtype=np.uint8),lambda name:SimpleNamespace(filtered_results=rows))['matches']['number']
    assert m['hit'] is True and m['text']=='0'
    assert 'filtered_candidates' not in m and 'ambiguous' not in m
