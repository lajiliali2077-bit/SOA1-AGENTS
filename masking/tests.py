"""Tests du service de masquage."""

from django.test import TestCase

from compiler.core import Block

from .services import mask_observations, recall_observation, record_observation


def obs(n):
    return Block("observation", f"Observation (get_invoice, obs-{n:04d}) :\n" + "ligne\n" * 100,
                 source=f"obs-{n:04d}")


class MaskingTests(TestCase):
    def test_enregistrer_puis_relire(self):
        obs_id = record_observation("get_invoice", "sortie complète")
        self.assertRegex(obs_id, r"^obs-\d{4}$")
        self.assertEqual(recall_observation(obs_id), "sortie complète")
        with self.assertRaises(ValueError):
            recall_observation("obs-9999")

    def test_garde_les_2_dernieres(self):
        blocks = [obs(1), obs(2), obs(3)]
        total = sum(b.tokens for b in blocks)
        new_blocks, masked = mask_observations(blocks, budget=total)
        self.assertEqual(masked, ["obs-0001"])
        self.assertEqual([b.kind for b in new_blocks], ["masked", "observation", "observation"])
        self.assertIn("[sortie masquée : get_invoice, 100 lignes", new_blocks[0].text)
        self.assertLess(new_blocks[0].tokens, blocks[0].tokens / 3)

    def test_rien_sous_le_seuil(self):
        blocks = [obs(1), obs(2), obs(3)]
        total = sum(b.tokens for b in blocks)
        self.assertEqual(mask_observations(blocks, budget=total * 2), (blocks, []))
