"""Pipeline ordering with injected preparation/capture; timings contain only numeric stages."""
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from naatik_next import timings
from naatik_next.app import Window
from tests import test_hotkey as fixtures
from tests.test_processes import APP


class PipelineTests(unittest.TestCase):
    tearDown = fixtures.HotkeyTests.tearDown
    png = fixtures.HotkeyTests.png

    def setUp(self):
        fixtures.HotkeyTests.setUp(self)
        self.w.settings['ocr_engine'] = 'mangaocr'
        APP.clipboard().setText('sentinel')

    def start_preparation(self):
        with patch.object(self.w.manga_task, 'start') as manga, patch.object(self.w.detect_task, 'start') as other:
            self.w.prepare_selected()
            other.assert_not_called()
            request = manga.call_args.args[0]
            self.assertEqual(request['action'], 'prepare')
        self.w.manga_task.busy = True
        return request['preparation']

    def prepared(self, identity):
        self.w.manga_task.busy = False
        self.w.manga_result(dict(id='mangaocr', name='MangaOCR', languages=[], status='listo',
                                 detail='fixture', preparation=identity))

    def test_copy_selector_runs_while_engine_loads_then_infers_once(self):
        identity = self.start_preparation()
        with patch.object(self.w.manga_task, 'start') as infer, patch.object(self.w.argos_task, 'start') as argos, \
                patch.object(self.w.selection_task, 'start') as dictionary:
            self.assertEqual(self.w.external_command('capture-copy'), 'accepted')
            self.assertEqual(self.w.capture_delay.interval(), 0)
            self.w.capture_delay.stop()
            self.w.captured(self.png())
            pending_image = self.w.copy_job['image']
            self.assertTrue(Path(pending_image).is_file())
            infer.assert_not_called()
            self.assertEqual(self.w.external_command('capture-copy'), 'ignored')
            self.assertEqual(self.w.capture_and_recognize(), 'ignored')
            self.prepared(identity)
            infer.assert_called_once()
            request = infer.call_args.args[0]
            self.w.recognized(dict(generation=request['generation'], text='日本'))
            self.assertEqual(APP.clipboard().text(), '日本')
            self.assertFalse(Path(pending_image).exists())
            argos.assert_not_called()
            dictionary.assert_not_called()

    def test_graphical_capture_and_hotkey_share_parallel_pipeline(self):
        for entry in ('button','hotkey'):
            identity = self.start_preparation()
            with patch.object(self.w.manga_task, 'start') as infer, patch.object(self.w, 'redetect_argos'):
                if entry == 'button':
                    self.w.capture_btn.click()
                else:
                    self.w.global_capture()
                self.w.capture_delay.stop()
                self.w.captured(self.png())
                self.assertIsNotNone(self.w.pending_capture_ocr)
                infer.assert_not_called()
                self.prepared(identity)
                infer.assert_called_once()
                self.w.cancel()

    def test_switching_selected_engine_ignores_previous_preparation_identity(self):
        identity = self.start_preparation()
        with patch.object(self.w, 'redetect_argos'):
            self.prepared(identity)
        with patch('naatik_next.app.QTimer.singleShot'), patch.object(self.w.detect_task, 'start') as tess, \
                patch.object(self.w.manga_task, 'start') as manga:
            self.w.engine.setCurrentIndex(self.w.engine.findData('tesseract'))
            self.w.prepare_selected()
            request = tess.call_args.args[0]
            self.assertEqual(request['engine'], 'tesseract')
            self.assertEqual(self.w.ocr_language.currentText(), 'jpn')
            manga.assert_not_called()
            self.w.detected([dict(id='tesseract', name='Tesseract', status='listo', languages=['jpn'],
                                 detail='fixture', preparation=request['preparation'])])
            self.assertIsNone(self.w.preparing_engine)
            self.assertEqual(self.w.engine.currentData(), 'tesseract')
            self.assertTrue(all('preparation' not in e for e in self.w.engines))
            self.prepared(identity)
            self.assertEqual(self.w.engine.currentData(), 'tesseract')

    def test_cancel_pending_image_and_obsolete_preparation_cannot_copy(self):
        identity = self.start_preparation()
        with patch.object(self.w.manga_task, 'start') as infer, patch('naatik_next.app.QMessageBox.warning') as modal:
            self.w.external_command('capture-copy')
            self.w.capture_delay.stop()
            self.w.captured(self.png())
            image = self.w.copy_job['image']
            self.w.cancel()
            self.assertFalse(Path(image).exists())
            self.prepared(identity)
            infer.assert_not_called()
            self.assertIsNone(self.w.copy_job)
            self.assertEqual(APP.clipboard().text(), 'sentinel')
            modal.assert_not_called()

    def test_background_does_not_open_dictionary_database_or_argos(self):
        with patch('naatik_next.app.Store') as store, patch('naatik_next.app.QTimer.singleShot'):
            background = Window(background=True)
        try:
            store.assert_not_called()
            self.assertIsNone(background.store)
            self.assertFalse(background.argos_task.busy)
        finally:
            background.close()

    def test_closed_window_callbacks_cannot_write_outside_fixture_profile(self):
        self.w.closing = True
        with patch('naatik_next.app.save_settings') as save, patch.object(self.w.argos_task, 'start') as argos:
            self.w.persist()
            self.w.argos_result({})
            self.w.detected([])
            self.w.redetect_argos()
            self.w.prepare_selected()
            self.w.redetect()
            save.assert_not_called()
            argos.assert_not_called()

    def test_signal_received_before_qt_shutdown_event_cannot_copy_a_late_result(self):
        self.w.ocr_pending = 42
        self.w.interrupted = lambda: True
        with patch.object(self.w.selection_task, 'start') as lookup:
            self.w.recognized(dict(generation=42, text='late fixture'))
        lookup.assert_not_called()
        self.assertEqual(APP.clipboard().text(), 'sentinel')
        self.assertNotEqual(self.w.editor.toPlainText(), 'late fixture')

    def test_recording_is_opt_in_and_rejects_payloads(self):
        target = Path(self.tmp.name) / 'XDG_STATE_HOME' / 'naatik-next/capture-timings.jsonl'
        with patch.dict(os.environ, {'NAATIK_TIMINGS': '0'}):
            timings.event('request', timings.identity())
        self.assertFalse(target.exists())
        with patch.dict(os.environ, {'NAATIK_TIMINGS': '1'}):
            trace = timings.identity()
            timings.event('request', trace)
            timings.event('private OCR text', trace)
            timings.event('inference_end', 'private OCR text')
        rows = [json.loads(line) for line in target.read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0]), {'stage','trace','pid','at_ns'})
        self.assertNotIn('private', target.read_text())

    def test_prepared_model_reused_without_probe(self):
        # No neural inference here: verify load/probe counts at the adapter boundary.
        with patch('socket.getaddrinfo'), patch('socket.socket.connect'), patch('socket.socket.connect_ex'):
            from naatik_next.manga_worker import Engine
        model = Mock(return_value='日本')
        path = Path(self.tmp.name) / 'model'
        path.mkdir()
        (path/'config.json').write_text('{"model_type":"vision-encoder-decoder"}')
        fake_torch = types.SimpleNamespace(set_num_threads=Mock())
        fake_manga = types.SimpleNamespace(MangaOcr=Mock(return_value=model))
        with patch('naatik_next.manga_worker.complete_model', return_value=True), \
                patch('naatik_next.manga_worker.importlib.metadata.version', return_value='fixture'), \
                patch.dict(sys.modules, {'torch': fake_torch, 'manga_ocr': fake_manga}):
            engine = Engine()
            self.assertEqual(engine.detect(str(path), probe=False)['status'], 'listo')
            engine.detect(str(path), probe=False)
            fake_manga.MangaOcr.assert_called_once_with(str(path), force_cpu=True)
            model.assert_not_called()
            engine.detect(str(path))
            self.assertEqual(model.call_count, 1)  # Only explicit diagnostic probes.
            self.assertEqual(fake_manga.MangaOcr.call_count, 1)
            (path/'config.json').write_text('{"model_type":"vision-encoder-decoder","changed":true}')
            engine.detect(str(path), probe=False)
            self.assertEqual(fake_manga.MangaOcr.call_count, 2)


class SelectionTimingTests(unittest.TestCase):
    def test_pointer_sampling_records_only_drag_transitions(self):
        import ctypes as C
        from naatik_next.selection_timing import DragTimer
        timer = DragTimer('1'*32)
        library = Mock()
        library.XOpenDisplay.return_value = 1
        library.XDefaultRootWindow.return_value = 1
        states = iter([0, 256, 0])
        def pointer(*args):
            state = next(states)
            C.cast(args[-1], C.POINTER(C.c_uint))[0] = state
            if state == 0 and library.XQueryPointer.call_count == 3:
                timer.stopping = True
            return 1
        library.XQueryPointer.side_effect = pointer
        with patch('naatik_next.selection_timing.C.CDLL', return_value=library), \
                patch('naatik_next.selection_timing.timings.event') as event:
            timer.watch(readable=lambda: False)
        self.assertEqual([call.args for call in event.call_args_list],
                         [('selection_user_begin', '1'*32), ('selection_user_end', '1'*32)])
        library.XCloseDisplay.assert_called_once_with(1)

    def test_sampling_is_disabled_by_default(self):
        from naatik_next.selection_timing import DragTimer
        with patch('naatik_next.selection_timing.timings.enabled', return_value=False), \
                patch('naatik_next.selection_timing.C.CDLL') as library:
            with DragTimer('1'*32) as timer:
                self.assertIsNone(timer.process)
            library.assert_not_called()

    def test_observer_is_reaped_on_exception_and_repeated_close(self):
        import subprocess
        from naatik_next.selection_timing import DragTimer
        process = Mock()
        process.stdin.closed = False
        process.wait.side_effect = [subprocess.TimeoutExpired('observer', 1),
                                    subprocess.TimeoutExpired('observer', .5), 0]
        with patch('naatik_next.selection_timing.timings.enabled', return_value=True), \
                patch('naatik_next.selection_timing.subprocess.Popen', return_value=process):
            timer = DragTimer('1'*32)
            with self.assertRaisesRegex(ValueError, 'fixture'):
                with timer:
                    raise ValueError('fixture')
            timer.close()
        process.stdin.close.assert_called_once()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 3)

    def test_observer_failure_does_not_prevent_capture(self):
        from naatik_next.selection_timing import DragTimer
        with patch('naatik_next.selection_timing.timings.enabled', return_value=True), \
                patch('naatik_next.selection_timing.subprocess.Popen', side_effect=OSError('fixture')):
            with DragTimer('1'*32) as timer:
                self.assertIsNone(timer.process)

    def test_report_preserves_unmeasured_gaps_and_parallel_stages(self):
        from tools.capture_timings import captures
        def event(stage, ms, trace='1'*32, pid=1):
            return dict(stage=stage, trace=trace, pid=pid, at_ns=int(ms*1e6))
        rows = captures([event('process_start',0,None), event('engine_prepare_begin',1,None),
                         event('request',2), event('engine_ready',20),
                         event('inference_begin',21,pid=2), event('inference_end',25,pid=2),
                         event('clipboard',26)])
        self.assertEqual(rows[0]['total_ms'], 24)
        self.assertEqual(rows[0]['engine_prepare_ms'], 19)
        self.assertEqual(rows[0]['inference_ms'], 4)
        self.assertIsNone(rows[0]['drag_ms'])
        self.assertIsNone(rows[0]['selection_window_ms'])


class CapabilityTests(unittest.TestCase):
    def test_spectacle_check_reused_and_invalidated_on_binary_change(self):
        from naatik_next.ocr import spectacle_capability
        spectacle_capability.cache_clear()
        def run(args, *unused):
            return 'spectacle 6.7.5' if '--version' in args else '--region --background --output --new-instance --release-capture'
        with patch('naatik_next.ocr.run', side_effect=run) as command:
            spectacle_capability('/fixture/spectacle', 1, 100)
            spectacle_capability('/fixture/spectacle', 1, 100)
            self.assertEqual(command.call_count, 2)
            spectacle_capability('/fixture/spectacle', 2, 101)
            self.assertEqual(command.call_count, 4)
        spectacle_capability.cache_clear()

    def test_tesseract_preparation_has_no_redundant_inference(self):
        from naatik_next.ocr import Tesseract
        with patch('naatik_next.ocr.shutil.which', return_value='/fixture/tesseract'), \
                patch('naatik_next.ocr.run', side_effect=['tesseract 5.5.0', 'languages:\njpn']), \
                patch.object(Tesseract, 'recognize') as infer:
            self.assertEqual(Tesseract().detect(probe=False)['status'], 'listo')
            infer.assert_not_called()
