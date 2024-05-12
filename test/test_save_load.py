import os
import tempfile
import unittest

import numpy as np

from cpprb import ReplayBuffer, PrioritizedReplayBuffer

def v(num: int, fname: str):
    return os.path.join(os.path.dirname(__file__), f"v{num}", fname)


class TestReplayBuffer(unittest.TestCase):
    def test_basic(self):
        """
        Basic Test Case

        Loaded buffer have same transitions with saved one.
        """
        buffer_size = 4
        env_dict = {"a": {}}

        rb1 = ReplayBuffer(buffer_size, env_dict)
        rb2 = ReplayBuffer(buffer_size, env_dict)
        rb3 = ReplayBuffer(buffer_size, env_dict)

        a = [1, 2, 3, 4]

        rb1.add(a=a)

        fname = "basic.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["a"], t3["a"])

    def test_smaller_buffer(self):
        """
        Load to smaller buffer

        Loaded buffer only stored last buffer_size transitions
        """
        buffer_size1 = 10
        buffer_size2 = 4
        env_dict = {"a": {}}

        rb1 = ReplayBuffer(buffer_size1, env_dict)
        rb2 = ReplayBuffer(buffer_size2, env_dict)
        rb3 = ReplayBuffer(buffer_size2, env_dict)

        a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        fname = "smaller.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"][-buffer_size2:],t2["a"])

    def test_load_to_filled_buffer(self):
        """
        Load to already filled buffer

        Add to transitions
        """
        buffer_size1 = 10
        buffer_size2 = 10
        env_dict = {"a": {}}

        rb1 = ReplayBuffer(buffer_size1, env_dict)
        rb2 = ReplayBuffer(buffer_size2, env_dict)
        rb3 = ReplayBuffer(buffer_size2, env_dict)

        a = [1, 2, 3, 4]
        b = [5, 6]

        rb1.add(a=a)
        rb2.add(a=b)
        rb3.add(a=b)

        fname="filled.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"][len(b):])
        np.testing.assert_allclose(t1["a"], t3["a"][len(b):])

    def test_load_Nstep(self):
        """
        Load Nstep transitions
        """
        buffer_size = 10
        env_dict = {"done": {}}
        Nstep = {"size": 3, "gamma": 0.99}

        rb1 = ReplayBuffer(buffer_size, env_dict, Nstep=Nstep)
        rb2 = ReplayBuffer(buffer_size, env_dict, Nstep=Nstep)
        rb3 = ReplayBuffer(buffer_size, env_dict, Nstep=Nstep)

        d = [0, 0, 0, 0, 1]

        rb1.add(done=d)
        rb1.on_episode_end()

        fname="Nstep.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["done"], t2["done"])
        np.testing.assert_allclose(t1["done"], t3["done"])

    def test_Nstep_incompatibility(self):
        """
        Raise ValueError when Nstep incompatibility
        """
        buffer_size = 10
        env_dict = {"done": {}}
        Nstep = {"size": 3, "gamma": 0.99}

        rb1 = ReplayBuffer(buffer_size, env_dict, Nstep=Nstep)
        rb2 = ReplayBuffer(buffer_size, env_dict)
        rb3 = ReplayBuffer(buffer_size, env_dict)

        d = [0, 0, 0, 0, 1]

        rb1.add(done=d)
        rb1.on_episode_end()

        fname="Nstep_raise.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))

            with self.assertRaises(ValueError):
                rb2.load_transitions(os.path.join(d, fname))

        with self.assertRaises(ValueError):
            rb3.load_transitions(v(1, fname))

    def test_next_of(self):
        """
        Load next_of transitions with safe mode

        For safe mode, next_of is not necessary at loaded buffer.
        """
        buffer_size = 10
        env_dict1 = {"a": {}}
        env_dict2 = {"a": {}, "next_a": {}}

        rb1 = ReplayBuffer(buffer_size, env_dict1, next_of="a")
        rb2 = ReplayBuffer(buffer_size, env_dict2)
        rb3 = ReplayBuffer(buffer_size, env_dict2)

        a = [1, 2, 3, 4, 5, 6]

        rb1.add(a=a[:-1], next_a=a[1:])

        fname="next_of.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1,fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"])
        np.testing.assert_allclose(t1["a"], t3["a"])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"])

    def test_unsafe_next_of(self):
        """
        Load next_of transitions with unsafe mode
        """
        buffer_size = 10
        env_dict = {"a": {}}

        rb1 = ReplayBuffer(buffer_size, env_dict, next_of="a")
        rb2 = ReplayBuffer(buffer_size, env_dict, next_of="a")
        rb3 = ReplayBuffer(buffer_size, env_dict, next_of="a")

        a = [1, 2, 3, 4, 5, 6]

        rb1.add(a=a[:-1], next_a=a[1:])

        fname="unsafe_next_of.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname), safe=False)
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"])
        np.testing.assert_allclose(t1["a"], t3["a"])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"])

    def test_unsafe_next_of_already_filled(self):
        """
        Load unsafe next_of transitions with already filled buffer
        """
        buffer_size = 10
        env_dict = {"a": {}}

        rb1 = ReplayBuffer(buffer_size, env_dict, next_of="a")
        rb2 = ReplayBuffer(buffer_size, env_dict, next_of="a")
        rb3 = ReplayBuffer(buffer_size, env_dict, next_of="a")

        a = [1, 2, 3, 4, 5, 6]
        b = [7, 8, 9]

        rb1.add(a=a[:-1], next_a=a[1:])
        rb2.add(a=b[:-1], next_a=b[1:])
        rb3.add(a=b[:-1], next_a=b[1:])

        fname="unsafe_next_of_already.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname), safe=False)
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        self.assertEqual(rb1.get_stored_size()+len(b)-1, rb2.get_stored_size())
        self.assertEqual(rb1.get_stored_size()+len(b)-1, rb3.get_stored_size())

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"][len(b)-1:])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"][len(b)-1:])
        np.testing.assert_allclose(t1["a"], t3["a"][len(b)-1:])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"][len(b)-1:])

    def test_incompatible_unsafe_next_of(self):
        """
        Load incompatible next_of transitions with unsafe mode
        """
        buffer_size = 10
        env_dict1 = {"a": {}}
        env_dict2 = {"a": {}, "next_a": {}}

        rb1 = ReplayBuffer(buffer_size, env_dict1, next_of="a")
        rb2 = ReplayBuffer(buffer_size, env_dict2)
        rb3 = ReplayBuffer(buffer_size, env_dict2)

        a = [1, 2, 3, 4, 5, 6]

        rb1.add(a=a[:-1], next_a=a[1:])

        fname="unsafe_incompatible_next_of.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname), safe=False)
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"])
        np.testing.assert_allclose(t1["a"], t3["a"])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"])

    def test_fulled_unsafe_next_of(self):
        """
        Load with already fulled buffer
        """
        buffer_size = 10
        env_dict = {"a": {}}

        rb1 = ReplayBuffer(buffer_size, env_dict, next_of="a")
        rb2 = ReplayBuffer(buffer_size, env_dict, next_of="a")
        rb3 = ReplayBuffer(buffer_size, env_dict, next_of="a")

        a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

        rb1.add(a=a[:-1], next_a=a[1:])

        fname="fulled_unsafe_next_of.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname), safe=False)
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"])
        np.testing.assert_allclose(t1["a"], t3["a"])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"])

    def test_stack_compress(self):
        """
        Load stack_compress transitions
        """
        buffer_size = 10
        env_dict = {"a": {"shape": 3}}

        rb1 = ReplayBuffer(buffer_size, env_dict, stack_compress="a")
        rb2 = ReplayBuffer(buffer_size, env_dict, stack_compress="a")
        rb3 = ReplayBuffer(buffer_size, env_dict, stack_compress="a")

        a = [[1, 2, 3],
             [2, 3, 4],
             [3, 4, 5],
             [4, 5, 6]]

        rb1.add(a=a)

        fname="stack_compress.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["a"], t3["a"])

    def test_incompatible_stack_compress(self):
        """
        Load incompatible stack_compress transitions with safe mode
        """
        buffer_size = 10
        env_dict = {"a": {"shape": 3}}

        rb1 = ReplayBuffer(buffer_size, env_dict, stack_compress="a")
        rb2 = ReplayBuffer(buffer_size, env_dict)
        rb3 = ReplayBuffer(buffer_size, env_dict)

        a = [[1, 2, 3],
             [2, 3, 4],
             [3, 4, 5],
             [4, 5, 6]]

        rb1.add(a=a)

        fname="incompatible_stack_compress.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["a"], t3["a"])

    def test_incompatible_unsafe_stack_compress(self):
        """
        Load incompatible stack_compress transitions with unsafe mode
        """
        buffer_size = 10
        env_dict = {"a": {"shape": 3}}

        rb1 = ReplayBuffer(buffer_size, env_dict, stack_compress="a")
        rb2 = ReplayBuffer(buffer_size, env_dict)
        rb3 = ReplayBuffer(buffer_size, env_dict)

        a = [[1, 2, 3],
             [2, 3, 4],
             [3, 4, 5],
             [4, 5, 6]]

        rb1.add(a=a)

        fname="incompatible_unsafe_stack_compress.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname), safe=False)
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["a"], t3["a"])

    def test_next_of_stack_compress(self):
        """
        Load next_of and stack_compress transitions
        """
        buffer_size = 10
        env_dict = {"a": {"shape": 3}}

        rb1 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")
        rb2 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")
        rb3 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")

        a = [[1, 2, 3],
             [2, 3, 4],
             [3, 4, 5],
             [4, 5, 6],
             [5, 6, 7],
             [6, 7, 8]]

        rb1.add(a=a[:-1], next_a=a[1:])

        fname="next_of_stack_compress.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname))
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"])
        np.testing.assert_allclose(t1["a"], t3["a"])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"])

    def test_unsafe_next_of_stack_compress(self):
        """
        Load next_of and stack_compress transitions
        """
        buffer_size = 10
        env_dict = {"a": {"shape": 3}}

        rb1 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")
        rb2 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")
        rb3 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")

        a = [[1, 2, 3],
             [2, 3, 4],
             [3, 4, 5],
             [4, 5, 6],
             [5, 6, 7],
             [6, 7, 8]]

        rb1.add(a=a[:-1], next_a=a[1:])

        fname="unsafe_next_of_stack_compress.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname), safe=False)
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"])
        np.testing.assert_allclose(t1["a"], t3["a"])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"])

    def test_unsafe_fulled_next_of_stack_compress(self):
        """
        Load unsafe fulled next_of and stack_compress transitions
        """
        buffer_size = 10
        env_dict = {"a": {"shape": 3}}

        rb1 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")
        rb2 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")
        rb3 = ReplayBuffer(buffer_size, env_dict, next_of="a", stack_compress="a")

        a = [[1, 2, 3],
             [2, 3, 4],
             [3, 4, 5],
             [4, 5, 6],
             [5, 6, 7],
             [6, 7, 8],
             [7, 8, 9],
             [8, 9,10],
             [9,10,11],
             [10,11,12],
             [11,12,13]]

        rb1.add(a=a[:-1], next_a=a[1:])

        fname="unsafe_fulled_next_of_stack_compress.npz"
        with tempfile.TemporaryDirectory(prefix="cpprb-") as d:
            rb1.save_transitions(os.path.join(d, fname), safe=False)
            rb2.load_transitions(os.path.join(d, fname))
        rb3.load_transitions(v(1, fname))

        t1 = rb1.get_all_transitions()
        t2 = rb2.get_all_transitions()
        t3 = rb3.get_all_transitions()

        np.testing.assert_allclose(t1["a"], t2["a"])
        np.testing.assert_allclose(t1["next_a"], t2["next_a"])
        np.testing.assert_allclose(t1["a"], t3["a"])
        np.testing.assert_allclose(t1["next_a"], t3["next_a"])

if __name__ == "__main__":
    unittest.main()
