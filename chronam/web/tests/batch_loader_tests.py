from datetime import date
import os

from django.test import TestCase

import chronam.web
from chronam.web.batch_loader import BatchLoader
from chronam.web.models import Title
from chronam.web.models import Batch
from chronam.settings import STORAGE

class BatchLoaderTest(TestCase):
    fixtures = ['countries.json', 'titles.json']

    def test_fixture(self):
        title = Title.objects.get(lccn = 'sn83030214')
        self.assertEqual(title.name, 'New-York tribune.')

    def test_load_batch(self):
        loader = BatchLoader(storage=STORAGE, process_ocr=False)
        batch = loader.load_batch('batch_dlc_jamaica_ver01')
        self.assertTrue(isinstance(batch, Batch))
        self.assertEqual(batch.name, 'batch_dlc_jamaica_ver01')
        self.assertEqual(len(batch.issues.all()), 304)

        title = Title.objects.get(lccn = 'sn83030214')
        self.assertTrue(title.has_issues())

        issue = batch.issues.all()[0]
        self.assertEqual(issue.volume, '63')
        self.assertEqual(issue.number, '20620')
        self.assertEqual(issue.edition, 1)
        self.assertEqual(issue.title.lccn, 'sn83030214')
        self.assertEqual(date.strftime(issue.date_issued, '%Y-%m-%d'), 
            '1903-05-01')
        self.assertEqual(len(issue.pages.all()), 14)

        page = issue.pages.all()[0]
        self.assertEqual(page.sequence, 1)
        self.assertEqual(page.url, u'/lccn/sn83030214/1903-05-01/ed-1/seq-1/')

        note = page.notes.all()[1]
        self.assertEqual(note.type, "noteAboutReproduction")
        self.assertEqual(note.text, "Present")

        # extract ocr data just for this page
        loader.process_ocr(page, index=False)
        #self.assertEqual(page.number, 1)
        self.assertEqual(page.sequence, 1)
        self.assertEqual(page.tiff_filename, 'sn83030214/00175042143/1903050101/0002.tif')
        self.assertEqual(page.jp2_filename, 'sn83030214/00175042143/1903050101/0002.jp2')
        self.assertEqual(page.jp2_length, 8898)
        self.assertEqual(page.jp2_width, 6520)
        self.assertEqual(page.ocr_filename, 'sn83030214/00175042143/1903050101/0002.xml')
        self.assertEqual(page.pdf_filename, 'sn83030214/00175042143/1903050101/0002.pdf')
        self.assertTrue(page.ocr != None)
        self.assertTrue(len(page.ocr.text) > 0)
        self.assertTrue(len(page.ocr.word_coordinates_json) > 0)

        p = Title.objects.get(lccn='sn83030214').issues.all()[0].pages.all()[0]
        self.assertTrue(p.ocr != None)

        # check that the solr_doc looks legit
        solr_doc = page.solr_doc
        self.assertEqual(solr_doc['id'], '/lccn/sn83030214/1903-05-01/ed-1/seq-1/')
        self.assertEqual(solr_doc['type'], 'page')
        self.assertEqual(solr_doc['sequence'], 1)
        self.assertEqual(solr_doc['lccn'], 'sn83030214')
        self.assertEqual(solr_doc['title'], 'New-York tribune.')
        self.assertEqual(solr_doc['date'], '19030501')
        self.assertEqual(solr_doc['batch'], 'batch_dlc_jamaica_ver01')
        self.assertEqual(solr_doc['subject'], [
            u'New York (N.Y.)--Newspapers.',
            u'New York County (N.Y.)--Newspapers.'])
        self.assertEqual(solr_doc['place'], [
            u'New York--Brooklyn--New York City', 
            u'New York--Queens--New York City'])
        self.assertEqual(solr_doc['note'], [
            u"I'll take Manhattan",
            u'The Big Apple'])
        self.assertTrue(not solr_doc.has_key('essay'))

        f = os.path.join(os.path.dirname(chronam.web.__file__), 'test-data', 
            'ocr.txt')
        self.assertEqual(solr_doc['ocr'], file(f).read().decode('utf-8'))

