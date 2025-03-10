from contextlib import contextmanager, suppress
import os
import tempfile
import unittest

import numpy as np

from cpprb import create_buffer, ReplayBuffer, PrioritizedReplayBuffer


@contextmanager
def TempDir(*args, **kwargs):
    # `ignore_cleanup_errors` is only supported 3.10+
    d = tempfile.TemporaryDirectory(*args, **kwargs)
    previous_dir = os.getcwd()
    os.chdir(d.name)
    try:
        yield
    finally:
        os.chdir(previous_dir)
        with suppress(PermissionError, NotADirectoryError):
            d.cleanup()


class TestFeatureHighDimensionalObs(unittest.TestCase):
    def test_RGB_screen_obs(self):
        size = 256
        obs_shape = (84,84,3)
        act_dim = 1

        rb = create_buffer(size,{"obs": {"shape": obs_shape},
                                 "act": {"shape": act_dim},
                                 "rew": {},
                                 "next_obs": {"shape": obs_shape},
                                 "done": {}},
                           prioritized = True)

        obs = np.ones(obs_shape,dtype=np.double)
        act = 2
        rew = 0.5
        next_obs = np.zeros_like(obs)
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        _o = rb._encode_sample(np.array((0)))["obs"]
        _no = rb._encode_sample(np.array((0)))["next_obs"]

        self.assertEqual(obs_shape,_o[0].shape)
        np.testing.assert_allclose(obs,_o[0])

        self.assertEqual(obs_shape,_no[0].shape)
        np.testing.assert_allclose(next_obs,_no[0])

    def test_BatchSampling(self):
        size = 256
        obs_shape = (84,84,3)
        act_dim = 1
        batch_size = 64

        rb = create_buffer(size,
                           {"obs": {"shape": obs_shape},
                            "act": {"shape": act_dim},
                            "rew": {},
                            "next_obs": {"shape": obs_shape},
                            "done": {}},
                           prioritized = True,
                           Nstep = {"size": 4, "rew": "rew","next": "next_obs"})

        obs = np.ones(obs_shape,dtype=np.double)
        act = 2
        rew = 0.5
        next_obs = np.zeros_like(obs)
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        rb.sample(batch_size)

class TestMemmap(unittest.TestCase):
    def test_memmap(self):
        with TempDir():
            rb = ReplayBuffer(32,{"done": {}},mmap_prefix="mmap")

            for _ in range(1000):
                rb.add(done=0.0)

            self.assertTrue(os.path.exists("mmap_done.dat"))


class TestShuffleTransitions(unittest.TestCase):
    def test_shuffle_transitions(self):
        rb = ReplayBuffer(64, {"a": { "dtype": np.int64 }})

        a = np.arange(64, dtype=np.int64)
        rb.add(a=a)

        s1 = rb.get_all_transitions()["a"]
        s2 = rb.get_all_transitions(shuffle=True)["a"]

        self.assertFalse((s1 == s2).all())
        self.assertFalse(set(np.ravel(s1)) ^ set(np.ravel(s2)))


if __name__ == '__main__':
    unittest.main()
