from itertools import compress

from django.test import TestCase
from pulpcore.plugin.models import Content, Repository, RepositoryVersion


class RepositoryVersionTestCase(TestCase):

    def setUp(self):
        self.repository = Repository.objects.create()
        self.repository.CONTENT_TYPES = [Content]
        self.repository.save()

        contents = []
        for _ in range(0, 20):
            contents.append(Content(pulp_type="core.content"))

        Content.objects.bulk_create(contents)
        self.pks = [c.pk for c in contents]
        self.one_content_qs = [Content.objects.filter(pk=pk) for pk in self.pks]

    def test_add_and_remove_content(self):
        contents = Content.objects.filter(pk__in=self.pks[:4])
        with self.repository.new_version() as version1:
            version1.add_content(contents)  # v1 == four content units

        to_remove = contents[0:2]
        with self.repository.new_version() as version2:
            version2.remove_content(to_remove)  # v2 == removed 2 first contents

        to_add = Content.objects.filter(pk=contents[0].pk)
        with self.repository.new_version() as version3:
            version3.add_content(to_add)  # v3 == added first content

        version0 = RepositoryVersion.objects.filter(number=0, repository=self.repository).first()

        self.assertEqual(version0.added().count(), 0)
        self.assertEqual(version1.added().count(), 4)
        self.assertEqual(version2.added().count(), 0)
        self.assertEqual(version3.added().count(), 1)

        self.assertEqual(version0.removed().count(), 0)
        self.assertEqual(version1.removed().count(), 0)
        self.assertEqual(version2.removed().count(), 2)
        self.assertEqual(version3.removed().count(), 0)

        self.assertEqual(version3.added(version0).count(), 3)
        self.assertEqual(version3.removed(version0).count(), 0)

        added_pks_0 = version3.added(version0).values_list('pk', flat=True)
        removed_pks_0 = version3.removed(version0).values_list('pk', flat=True)

        self.assertCountEqual(added_pks_0, compress(self.pks, [1, 0, 1, 1]), added_pks_0)
        self.assertCountEqual(removed_pks_0, compress(self.pks, [0, 0, 0, 0]), removed_pks_0)

        added_pks_1 = version3.added(version1).values_list('pk', flat=True)
        removed_pks_1 = version3.removed(version1).values_list('pk', flat=True)

        self.assertCountEqual(added_pks_1, compress(self.pks, [0, 0, 0, 0]), added_pks_1)
        self.assertCountEqual(removed_pks_1, compress(self.pks, [0, 1, 0, 0]), removed_pks_1)

        added_pks_2 = version3.added(version2).values_list('pk', flat=True)
        removed_pks_2 = version3.removed(version2).values_list('pk', flat=True)

        self.assertCountEqual(added_pks_2, compress(self.pks, [1, 0, 0, 0]), added_pks_2)
        self.assertCountEqual(removed_pks_2, compress(self.pks, [0, 0, 0, 0]), removed_pks_2)

    def content_qs(self, pks):
        return Content.objects.filter(pk__in=pks)

    def test_regularize_content(self):
        with self.repository.new_version() as version1:
            version1.add_content(self.content_qs(self.pks[:5]))  # v1 == content 0-4

        # v2 content:
        # 0 leave as is
        # 1 remove
        # 2 remove, re-add
        # 3 remove, re-add, remove
        # 4 remove, re-add, remove, re-add
        # 5 add
        # 6 add, remove
        # 7 add, remove, re-add
        # 8 add, remone, re-add, remove
        # Expected content: 0, 2, 4, 5, 7
        # Added: 5, 7
        # Removed: 1, 3
        with self.repository.new_version() as version2:  # v2 == content 0, 1 and 3
            version2.remove_content(self.content_qs(self.pks[1:5]))
            version2.add_content(self.content_qs(self.pks[2:5]))
            version2.remove_content(self.content_qs(self.pks[3:5]))
            version2.add_content(self.content_qs(self.pks[4:5]))

            version2.add_content(self.content_qs(self.pks[5:9]))
            version2.remove_content(self.content_qs(self.pks[6:9]))
            version2.add_content(self.content_qs(self.pks[7:9]))
            version2.remove_content(self.content_qs(self.pks[8:9]))

        content_pks_1 = version1.content.values_list('pk', flat=True)
        added_pks_1 = version1.added().values_list('pk', flat=True)
        removed_pks_1 = version1.removed().values_list('pk', flat=True)

        self.assertCountEqual(content_pks_1, self.pks[0:5], content_pks_1)
        self.assertCountEqual(removed_pks_1, [], removed_pks_1)
        self.assertCountEqual(added_pks_1, self.pks[0:5], added_pks_1)

        content_pks_2 = version2.content.values_list('pk', flat=True)
        added_pks_2 = version2.added().values_list('pk', flat=True)
        removed_pks_2 = version2.removed().values_list('pk', flat=True)

        self.assertCountEqual(
            content_pks_2, compress(self.pks, [1, 0, 1, 0, 1, 1, 0, 1]), content_pks_1
        )
        self.assertCountEqual(removed_pks_2, compress(self.pks, [0, 1, 0, 1]), removed_pks_2)
        self.assertCountEqual(
            added_pks_2, compress(self.pks, [0, 0, 0, 0, 0, 1, 0, 1]), added_pks_2
        )
