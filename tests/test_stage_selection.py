import json
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from driver_epic_seven.config import ROOT, load_config
from driver_epic_seven.stages import StageInspector, check_start, compile_pipeline, parse_energy
from driver_epic_seven.vision import Vision
from driver_epic_seven.chapters import compile_chapter
from fixture_cache import transition_overrides


@pytest.mark.parametrize("energy,budget,cleared", [
    ({"cost":18,"available":912},20,False),
    ({"cost":8,"available":7},8,False),
    ({"cost":8,"available":912},7,False),
    ({"cost":8,"available":912},8,True),
])
def test_start_guards_reject_wrong_cost_budget_energy_or_replay(energy,budget,cleared):
    with pytest.raises(ValueError):
        check_start({"energy":8},{"identity_verified":True,"energy":energy,"already_cleared":cleared},budget)


def test_low_confidence_cost_is_not_accepted():
    assert parse_energy([{"text":"8/912","score":.65}]) is None


def test_prepare_does_not_compile_a_start_action():
    prepared=compile_pipeline("pen001","prepare")
    assert prepared["Stage.CheckReady"].get("action","DoNothing")=="DoNothing"
    start=compile_pipeline("pen001","start",8)
    assert start["Stage.CheckReady"]["max_hit"]==1
    assert start["Stage.CheckReady"]["timeout"]==90000
    assert start["Stage.CheckReady"]["custom_recognition_param"]["max_energy"]==8
    assert start["Stage.CheckReady"]["custom_recognition_param"]["allow_replay"] is False


def test_episode_number_is_not_a_substring_match():
    assert StageInspector._exact([{"text":"Episode 12","score":.99}],"Episode 2") is None


def test_chapter_budget_and_single_start_per_stage():
    config=load_config()
    with pytest.raises(ValueError,match="orçamento"):
        compile_chapter(config,"pes004",27)
    plan,graph=compile_chapter(config,"pes004",28)
    assert plan["stage_ids"]==["pes004","pes005","pes006"]
    assert plan["energy_limit"]==28 and plan["max_starts"]==3
    for stage in plan["stage_ids"]:
        assert graph[f"Chapter.{stage}.Stage.CheckReady"]["max_hit"]==1
    assert graph["Chapter.pes006.Finish.VerifyDone"]["next"]==["Chapter.Done"]


def test_chapter_resume_finishes_current_without_starting_it_again():
    plan,graph=compile_chapter(load_config(),"pes005",20,finish_current=True)
    assert plan["stage_ids"]==["pes005","pes006"] and plan["max_starts"]==2
    assert graph["Chapter.Entry"]["next"]==["Chapter.Current.Finish.Entry"]
    assert graph["Chapter.Current.Finish.VerifyDone"]["next"]==["Chapter.pes005.Stage.Entry"]
    assert not any(name.startswith("Chapter.Current.Stage.") for name in graph)


@pytest.fixture(scope="module")
def stage_engine(tmp_path_factory):
    config=load_config()
    if not (ROOT/"tests/fixtures/local/32_ready_stage_two.png").exists():
        pytest.skip("Capturas da calibração não disponíveis neste checkout.")
    if not (config["resource_dir"]/"model/ocr/en_us/rec.onnx").exists():
        pytest.skip("Modelo OCR local não instalado; execute tools/install_ocr.py.")
    from maa.custom_recognition import CustomRecognition
    from maa.resource import Resource
    from maa.tasker import Tasker
    from maa.library import Library
    from maa.pipeline import JCustomRecognition
    from maa.define import LoggingLevelEnum
    Tasker.set_stdout_level(LoggingLevelEnum.Off)
    Tasker.set_log_dir(tmp_path_factory.mktemp("stage_ocr")/"maa")
    vision=Vision(config["vision_file"],config["resource_dir"])
    inspector=StageInspector(config["stage_file"])
    campaign_inspector=StageInspector(ROOT/"data/stages/campaign.json")
    observations=[]
    class Recognition(CustomRecognition):
        def analyze(self,context,argv):
            params=json.loads(argv.custom_recognition_param)
            # The shared offline cache validates pixels, effective nodes,
            # configuration, templates and models. No frame-only cache here.
            analysis=vision.inspect(argv.image,lambda name:context.run_recognition(name,argv.image))
            analysis['window']={'process_name':'EpicSeven.exe','client_size':[1212,682]}
            if params.get('read_text'):
                analysis['text']=StageInspector._ocr(
                    lambda kind,args:context.run_recognition_direct(kind,args,argv.image),(0,0,1212,682))
            if params.get("stage_id"):
                chosen=inspector if params["stage_id"] in inspector.catalog else campaign_inspector
                analysis["stage"]=chosen.inspect(params["stage_id"],analysis,
                    lambda kind,args:context.run_recognition_direct(kind,args,argv.image))
            observations.append(analysis)
            if params.get("observe"):
                box=[0,0,1,1]
            elif params.get("stage_id"):
                box=inspector.target(analysis,params)
            else:
                box=vision.target(analysis,params)
            return self.AnalyzeResult(box=box,detail=analysis)

    resource=Resource()
    resource.set_cpu()
    resource.register_custom_recognition("ScreenTarget",Recognition())
    assert resource.post_bundle(config["resource_dir"]).wait().succeeded

    class Engine:
        @staticmethod
        def frame(name):
            return np.asarray(Image.open(ROOT/"tests/fixtures/local"/name).convert("RGB"))[:,:,::-1].copy()

        @staticmethod
        def inspect(name,stage_id):
            tasker=Tasker()
            assert Library.framework().MaaTaskerBindResource(tasker._handle,resource._handle)
            params=JCustomRecognition(custom_recognition="ScreenTarget",custom_recognition_param={"observe":True,"stage_id":stage_id})
            assert tasker.post_recognition("Custom",params,Engine.frame(name)).wait().succeeded
            return observations[-1]

    Engine.resource=resource
    return Engine


def test_ready_identity_and_cost_from_actual_capture(stage_engine):
    observed=stage_engine.inspect("21_battle_ready.png","pen001")["stage"]
    assert observed["identity_verified"]
    assert observed["energy"]["cost"]==8
    assert observed["energy"]["available"]==920
    assert observed["already_cleared"] is False


@pytest.mark.fixtures
def test_current_ready_label_recognizes_stage_and_rejects_supporter(stage_engine):
    current=ROOT/'var/runs/20261103T173243Z_2704a4c0/observation.png'
    animated=ROOT/'var/runs/20261103T175641Z_1310e932/stage_before.png'
    if not current.exists() or not animated.exists():
        pytest.skip('Captura privada da variante atual indisponível.')
    for frame in (current,animated):
        result=stage_engine.inspect(frame,'poe007')
        assert result['state']=='battle_ready'
        assert result['stage']['identity_verified']
        assert result['stage']['energy']['cost']==16
    from driver_epic_seven.vision import pixel_error
    template=np.asarray(Image.open(ROOT/'resources/epic-seven/image/start_quest_current.png').convert('RGB'))[:,:,::-1].copy()
    dim=(np.asarray(Image.open(animated).convert('RGB'))[:,:,::-1]*.5).astype(np.uint8)
    assert pixel_error(dim,template,[1031,610,110,28],glyph_min=200)>14
    supporter=stage_engine.inspect('31_supporter_reread.png','pen001')
    assert supporter['state']!='battle_ready'


@pytest.mark.fixtures
def test_episode5_title_is_read_without_adjacent_record_badge(stage_engine):
    frame=ROOT/'var/runs/20261103T195417Z_b0e8fd86/stage_before.png'
    if not frame.exists():
        pytest.skip('Captura privada da fase indisponível.')
    current=stage_engine.inspect(frame,'sks007')
    assert current['state']=='supporter_selection'
    assert current['stage']['identity_verified'], current['stage']['ocr']['title'][-1]
    assert not stage_engine.inspect(frame,'sks008')['stage']['identity_verified']


def test_joined_record_badge_requires_exact_title_position_and_confidence():
    title='Reality, Ideals, and Struggle'
    row={'text':title+' No Record','score':.97,'box':[877,112,323,28]}
    assert StageInspector._story_title([row],title)=='exact_with_no_record_badge'
    for change in ({'text':'Another story No Record'},{'score':.94},{'box':[600,112,323,28]},
                   {'text':title+' No Record Extra'}):
        assert StageInspector._story_title([{**row,**change}],title) is None


def test_ready_energy_region_preserves_first_digit_of_two_digit_cost(stage_engine):
    observed=stage_engine.inspect("55_ready_energy_first_digit.png","dra007")["stage"]
    assert observed["identity_verified"]
    assert observed["energy"]["cost"]==16
    assert observed["energy"]["available"]==1106
    check_start({"energy":16},observed,16)


def test_wrong_requested_stage_is_rejected_from_same_capture(stage_engine):
    assert stage_engine.inspect("21_battle_ready.png","pen002")["stage"]["identity_verified"] is False


def test_location_line_retry_preserves_exact_identity(stage_engine):
    assert stage_engine.inspect("31_supporter_reread.png","pen001")["stage"]["identity_verified"]


def test_tight_title_reread_keeps_roman_two_and_correct_location(stage_engine):
    current=stage_engine.inspect("42_supporter_roman_two.png","con002")["stage"]
    assert current["identity_verified"] and current["title_match_method"]=="exact"
    assert not stage_engine.inspect("42_supporter_roman_two.png","con001")["stage"]["identity_verified"]


def test_title_reread_preserves_third_roman_glyph(stage_engine):
    assert stage_engine.inspect("43_supporter_roman_three.png","con009")["stage"]["identity_verified"]
    assert not stage_engine.inspect("43_supporter_roman_three.png","con008")["stage"]["identity_verified"]


def test_small_multiline_chapter_header_is_reread_without_name_replacement(stage_engine):
    observed=stage_engine.inspect("44_chapter_eight_map.png","sha001")["stage"]
    assert observed["context_verified"] and observed["identity_verified"]
    assert not stage_engine.inspect("44_chapter_eight_map.png","pen001")["stage"]["context_verified"]


def test_description_reread_recovers_clipped_descender_without_fuzzy_matching(stage_engine):
    observed=stage_engine.inspect("46_map_description_descender.png","sha006")["stage"]
    assert observed["identity_verified"] and observed["context_verified"]
    assert "Inquisitor" in observed["ocr"]["description"][0]["text"]
    assert not stage_engine.inspect("46_map_description_descender.png","sha007")["stage"]["identity_verified"]


def test_trial_supporter_caption_and_record_label_do_not_change_stage_identity(stage_engine):
    observed=stage_engine.inspect("48_supporter_trial.png","dis003")
    assert observed["state"]=="supporter_selection" and observed["stage"]["identity_verified"]
    assert not stage_engine.inspect("48_supporter_trial.png","dis002")["stage"]["identity_verified"]


def test_calibrated_location_excludes_only_observed_source_prefix(stage_engine):
    observed=stage_engine.inspect("49_supporter_numeric_source_prefix.png","pow005")["stage"]
    assert observed["identity_verified"]
    assert not stage_engine.inspect("49_supporter_numeric_source_prefix.png","pow004")["stage"]["identity_verified"]
    inspector=StageInspector(ROOT/"data/stages/campaign.json")
    assert inspector.get("pow005")["location_source_text"]=="2.5 District B Gate"
    assert inspector.get("sks006")["location"]=="6th District Camp"


def test_loading_supporter_panel_does_not_allow_select_team(stage_engine):
    observed=stage_engine.inspect("22_supporter_selection.png","pen001")
    assert observed["stage"]["identity_verified"]
    assert observed["stage"]["supporter_loading"]
    inspector=StageInspector(load_config()["stage_file"])
    assert inspector.target(observed,{"state":"supporter_selection","target":"stage_select_team"}) is None


def test_padlock_blocks_a_readable_locked_stage(stage_engine):
    observed=stage_engine.inspect("29_episode_map.png","pen003")["stage"]
    assert observed["context_verified"]
    assert observed["row_locked"] is True


def test_scroll_uses_readable_list_range_and_requested_ordinal(stage_engine):
    observed=stage_engine.inspect("29_episode_map.png","pes006")
    inspector=StageInspector(load_config()["stage_file"])
    assert observed["stage"]["visible_ordinals"]
    assert inspector.target(observed,{"state":"episode_map","target":"scroll_down"})
    assert inspector.target(observed,{"state":"episode_map","target":"scroll_top"}) is None


def test_next_stage_selected_and_ready_have_consistent_identity(stage_engine):
    observed=stage_engine.inspect("29_episode_map.png","pen002")["stage"]
    assert observed["context_verified"] and observed["identity_verified"]
    assert observed["row_locked"] is False
    ready=stage_engine.inspect("32_ready_stage_two.png","pen002")["stage"]
    assert ready["identity_verified"] and ready["energy"]["available"]==912


def test_replay_ui_requires_explicit_permission(stage_engine):
    observed=stage_engine.inspect("30_ready_replay.png","pen001")["stage"]
    assert observed["identity_verified"] and observed["already_cleared"]
    with pytest.raises(ValueError,match="concluída"):
        check_start({"energy":8},observed,8)


def test_native_start_pipeline_in_offline_controller_starts_once(stage_engine):
    from maa.controller import CustomController
    from maa.tasker import Tasker

    class OfflineController(CustomController):
        def __init__(self):
            self.current=stage_engine.frame("21_battle_ready.png")
            self.clicks=[]
            super().__init__()
        def connect(self):return True
        def request_uuid(self):return "offline-only-stage-test"
        def get_features(self):return 0
        def screencap(self):return self.current.copy()
        def click(self,x,y):
            self.clicks.append((x,y))
            self.current=stage_engine.frame("23_story.png")
            return True
        def unexpected(self,*args):raise AssertionError("Unexpected input in offline simulation")
        start_app=stop_app=swipe=touch_down=touch_move=touch_up=click_key=input_text=key_down=key_up=unexpected

    controller=OfflineController()
    controller.set_screenshot_use_raw_size(True)
    assert controller.post_connection().wait().succeeded
    tasker=Tasker()
    assert tasker.bind(stage_engine.resource,controller)
    definitions=json.loads((load_config()['resource_dir']/'pipeline/stage_selection.json').read_text(encoding='utf-8'))
    job=tasker.post_task("Stage.Entry",transition_overrides(definitions,compile_pipeline("pen001","start",8))).wait()
    assert job.succeeded
    assert len(controller.clicks)==1
    assert any(node.name=="Stage.EnteredStory" and node.completed for node in job.get().nodes)


def test_finish_pipeline_retries_unchanged_confirmation_and_result_offline(stage_engine):
    from maa.controller import CustomController
    from maa.tasker import Tasker

    class OfflineFinishController(CustomController):
        def __init__(self):
            self.names=["23_story.png","24_story_confirmation.png","26_stage_clear.png",
                        "27_battle_rewards.png","35_side_story_alert.png","36_friend_request.png","40_friendship_tap_to_close.png","41_rank_up.png","47_connection_unlocked.png",
                        "23_story.png","24_story_confirmation.png","28_story_reward.png",
                        "37_received_reward.png","37_received_reward.png","29_episode_map.png"]
            self.index=0
            self.clicks=[]
            self.ignored=set()
            super().__init__()
        def connect(self):return True
        def request_uuid(self):return "offline-only-finish-test"
        def get_features(self):return 0
        def screencap(self):return stage_engine.frame(self.names[self.index])
        def click(self,x,y):
            self.clicks.append((x,y))
            if self.index in (1,3) and self.index not in self.ignored:
                self.ignored.add(self.index)
                return True
            self.index+=1
            assert self.index<len(self.names), "Extra click after reaching the map"
            return True
        def unexpected(self,*args):raise AssertionError("Unexpected input in offline finish")
        start_app=stop_app=swipe=touch_down=touch_move=touch_up=click_key=input_text=key_down=key_up=unexpected

    controller=OfflineFinishController()
    controller.set_screenshot_use_raw_size(True)
    assert controller.post_connection().wait().succeeded
    tasker=Tasker()
    assert tasker.bind(stage_engine.resource,controller)
    definitions=json.loads((load_config()['resource_dir']/'pipeline/battle_finish.json').read_text(encoding='utf-8'))
    override=transition_overrides(definitions)
    job=tasker.post_task("Finish.Entry",override).wait()
    assert job.succeeded
    assert len(controller.clicks)==16
    assert controller.ignored=={1,3}
    assert any(node.name=="Finish.VerifyDone" and node.completed for node in job.get().nodes)


def test_chapter_native_graph_advances_two_stages_without_another_task(stage_engine,tmp_path):
    from maa.controller import CustomController
    from maa.tasker import Tasker
    config=load_config()
    catalog=json.loads(config["stage_file"].read_text(encoding="utf-8"))
    catalog["stages"]={key:catalog["stages"][key] for key in ("pen001","pen002")}
    path=tmp_path/"stages.json"
    path.write_text(json.dumps(catalog),encoding="utf-8")
    plan,graph=compile_chapter({**config,"stage_file":path},"pen001",16)
    graph=transition_overrides(graph)

    class ChapterController(CustomController):
        def __init__(self):
            self.names=["21_battle_ready.png","23_story.png","24_story_confirmation.png",
                "26_stage_clear.png","27_battle_rewards.png","28_story_reward.png","29_episode_map.png",
                "39_supporter_stage_two.png","32_ready_stage_two.png","23_story.png","24_story_confirmation.png",
                "26_stage_clear.png","27_battle_rewards.png","28_story_reward.png","29_episode_map.png"]
            self.index=0
            self.clicks=[]
            super().__init__()
        def connect(self):return True
        def request_uuid(self):return "offline-only-chapter-test"
        def get_features(self):return 0
        def screencap(self):return stage_engine.frame(self.names[self.index])
        def click(self,x,y):
            self.clicks.append((x,y));self.index+=1
            assert self.index<len(self.names),"Click after completing the chapter plan"
            return True
        def unexpected(self,*args):raise AssertionError("Unexpected input in offline chapter")
        start_app=stop_app=swipe=touch_down=touch_move=touch_up=click_key=input_text=key_down=key_up=unexpected

    controller=ChapterController();controller.set_screenshot_use_raw_size(True)
    assert controller.post_connection().wait().succeeded
    tasker=Tasker();assert tasker.bind(stage_engine.resource,controller)
    job=tasker.post_task("Chapter.Entry",graph).wait()
    assert job.succeeded
    assert len(controller.clicks)==14
    assert plan["max_starts"]==2
    assert any(node.name=="Chapter.Done" and node.completed for node in job.get().nodes)
    assert sum(node.name.endswith("Stage.CheckReady") and node.completed for node in job.get().nodes)==2


@pytest.mark.temporal
def test_intro_longpress_releases_mouse_before_dialog_skip(stage_engine):
    import time
    from maa.controller import CustomController
    from maa.tasker import Tasker

    class IntroController(CustomController):
        def __init__(self):
            self.names=["45_story_intro.png","23_story.png","24_story_confirmation.png",
                        "26_stage_clear.png","27_battle_rewards.png","28_story_reward.png","29_episode_map.png"]
            self.index=0;self.events=[];self.pressed=False
            super().__init__()
        def connect(self):return True
        def request_uuid(self):return "offline-only-intro-hold"
        def get_features(self):return 1
        def screencap(self):return stage_engine.frame(self.names[self.index])
        def touch_down(self,*args):
            assert not self.pressed
            self.pressed=True;self.events.append(("down",self.index,time.monotonic()));return True
        def touch_up(self,*args):
            assert self.pressed
            self.pressed=False;self.events.append(("up",self.index,time.monotonic()));self.index+=1
            assert self.index<len(self.names)
            return True
        def click(self,x,y):
            raise AssertionError("Controller advertises mouse down/up support")
        def unexpected(self,*args):raise AssertionError("Unexpected input in intro simulation")
        start_app=stop_app=swipe=touch_move=click_key=input_text=key_down=key_up=unexpected

    controller=IntroController();controller.set_screenshot_use_raw_size(True)
    assert controller.post_connection().wait().succeeded
    tasker=Tasker();assert tasker.bind(stage_engine.resource,controller)
    definitions=json.loads((load_config()["resource_dir"]/"pipeline/battle_finish.json").read_text(encoding="utf-8"))
    override=transition_overrides(definitions)
    job=tasker.post_task("Finish.Entry",override).wait()
    assert job.succeeded
    assert [(kind,index) for kind,index,_ in controller.events]==[(kind,index) for index in range(6) for kind in ("down","up")]
    assert controller.events[1][2]-controller.events[0][2]>=1.3
    assert not controller.pressed


def test_failed_battle_stops_without_leave_continue_or_retry_input(stage_engine):
    from maa.controller import CustomController
    from maa.tasker import Tasker

    class FailedController(CustomController):
        def connect(self):return True
        def request_uuid(self):return "offline-only-failed-battle"
        def get_features(self):return 0
        def screencap(self):return stage_engine.frame("53_battle_failed.png")
        def unexpected(self,*args):raise AssertionError("Failure screen must not receive input")
        start_app=stop_app=swipe=touch_down=touch_move=touch_up=click_key=input_text=key_down=key_up=click=unexpected

    controller=FailedController();controller.set_screenshot_use_raw_size(True)
    assert controller.post_connection().wait().succeeded
    tasker=Tasker();assert tasker.bind(stage_engine.resource,controller)
    job=tasker.post_task("Finish.Entry",{"Finish.Entry":{"timeout":1500}}).wait()
    assert job.succeeded
    assert any(node.name=="Finish.Defeat" and node.completed for node in job.get().nodes)
    assert not any(node.name=="Finish.VerifyDone" for node in job.get().nodes)


def test_rankup_and_info_notice_can_precede_clear(stage_engine):
    from maa.controller import CustomController
    from maa.tasker import Tasker

    class NoticeController(CustomController):
        def __init__(self):
            self.names=["41_rank_up.png","40_friendship_tap_to_close.png","26_stage_clear.png",
                        "27_battle_rewards.png","28_story_reward.png","29_episode_map.png"]
            self.index=0;super().__init__()
        def connect(self):return True
        def request_uuid(self):return "offline-only-notices-before-clear"
        def get_features(self):return 0
        def screencap(self):return stage_engine.frame(self.names[self.index])
        def click(self,x,y):
            self.index+=1
            assert self.index<len(self.names),"Input after returning to map"
            return True
        def unexpected(self,*args):raise AssertionError("Unexpected input in notice sequence")
        start_app=stop_app=swipe=touch_down=touch_move=touch_up=click_key=input_text=key_down=key_up=unexpected

    controller=NoticeController();controller.set_screenshot_use_raw_size(True)
    assert controller.post_connection().wait().succeeded
    tasker=Tasker();assert tasker.bind(stage_engine.resource,controller)
    definitions=json.loads((load_config()['resource_dir']/'pipeline/battle_finish.json').read_text(encoding='utf-8'))
    overrides=transition_overrides(definitions)
    job=tasker.post_task("Finish.Entry",overrides).wait()
    assert job.succeeded and controller.index==5
    assert any(node.name=="Finish.Clear" and node.completed for node in job.get().nodes)
    assert any(node.name=="Finish.VerifyDone" and node.completed for node in job.get().nodes)
