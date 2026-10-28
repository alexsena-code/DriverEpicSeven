"""Screen-reading contracts independent of hero names or progression actions."""
from copy import deepcopy
import json

import pytest

from driver_epic_seven.config import ROOT
from driver_epic_seven.observed_ui import build_tree, operation_view


@pytest.mark.fixtures
@pytest.mark.parametrize('run,number,old_name,expected', [
    ('20261027T091912Z_5e4ad40e',9,'Free Spirit Tieria','hero_awakening'),
    ('20261027T091912Z_5e4ad40e',16,'Free Spirit Tieria','hero_awakening'),
    ('20261027T091912Z_5e4ad40e',22,'Free Spirit Tieria','hero_detail'),
    ('20261027T065733Z_52d8869f',90,'Arbiter Vildred','hero_level_up'),
    ('20261027T065733Z_52d8869f',3,'Arbiter Vildred','hero_equipment'),
    ('20261027T084618Z_f4017642',30,'Free Spirit Tieria','connections'),
    ('20261027T060242Z_390d2724',178,'Arbiter Vildred','moonlight_blessing'),
    ('20261027T085923Z_aaae21c1',5,'Free Spirit Tieria','hero_presentation'),
    ('20261027T060242Z_390d2724',26,'Kise','hero_presentation'),
    ('20261027T055006Z_d1c129f7',7,'Renoa','hero_presentation'),
    ('20261027T081838Z_d968bc8e',69,'Free Spirit Tieria','connection_unlock_notice'),
])
def test_content_changes_do_not_require_character_matches_or_execute_actions(monkeypatch,run,number,old_name,expected):
    from driver_epic_seven.runtime import Runtime
    def forbidden(*args, **kwargs):
        pytest.fail('A screen reader attempted a runtime connection or input.')
    monkeypatch.setattr(Runtime,'__init__',forbidden)
    monkeypatch.setattr(Runtime,'primitive',forbidden)
    path=ROOT/'var/runs'/run/f'agent_{number:06}.json'
    if not path.exists():pytest.skip('Private screen fixture unavailable.')
    data=json.loads(path.read_text(encoding='utf-8'))['result']
    data['state']='unknown'
    # The Hero-tab marker is a generic tab glyph despite its legacy key name;
    # all character identity and story/action recognizers are absent here.
    data['matches']={key:value for key,value in data.get('matches',{}).items() if key=='victorika_hero_tab'}
    for row in data['text']:
        row['text']=row['text'].replace(old_name,'Uncatalogued Hero')
        if 'beautiful and lonely' in row['text']:
            row['text']='A different biography'
    original=deepcopy(data)
    tree=build_tree(data)
    current=operation_view({'ui_tree':tree})
    assert current['view']==expected
    assert any('Uncatalogued Hero' in str(item) for item in current['items'])
    assert data==original
    assert all(control['enabled'] is None for control in current['controls'])
    for item in current['items']:
        for field in ('acquired','application_completed','confirmation_sent','received','equipped'):
            assert item.get(field) is None


def test_awakening_layout_can_be_read_with_no_character_identity():
    rows=[('Awaken',[1010,615,80,25]),('Potential Stone',[950,170,180,25]),
          ('Hero Awakening Reward',[950,235,200,25]),('Consumed Resource',[960,470,180,25]),
          ('3/12',[1030,560,50,20]),('Defense',[980,300,90,20])]
    data={'state':'unknown','window':{'process_name':'EpicSeven.exe','client_size':[1212,682]},
          'matches':{},'text':[{'text':t,'box':box,'score':.99} for t,box in rows]}
    current=operation_view({'ui_tree':build_tree(data)})
    assert current['view']=='hero_awakening' and current['mode']=='preview'
    assert current['items'][0]['hero_name'] is None
    assert current['items'][0]['material_ratio']=={'available':3,'cost':12}
    assert current['controls'][0]['enabled'] is None
    data['text']=[r for r in data['text'] if r['text']!='Hero Awakening Reward']
    assert operation_view({'ui_tree':build_tree(data)})=={}
