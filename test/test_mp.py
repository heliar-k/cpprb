from multiprocessing import Process, get_context
from multiprocessing.context import ProcessError
from multiprocessing.managers import SyncManager
import unittest
import sys

import numpy as np

from cpprb import (MPReplayBuffer as ReplayBuffer,
                   MPPrioritizedReplayBuffer as PrioritizedReplayBuffer)

def add(rb):
    for _ in range(100):
        rb.add(done=0)

def sample(rb,batch_size):
    for _ in range(10):
        rb.sample(batch_size)

def add_args(rb,args):
    for arg in args:
        rb.add(**arg)

class TestReplayBuffer(unittest.TestCase):
    def test_buffer(self):

        buffer_size = 256
        obs_shape = (15,15)
        act_dim = 5

        N = 512

        erb = ReplayBuffer(buffer_size,{"obs":{"shape": obs_shape},
                                        "act":{"shape": act_dim},
                                        "rew":{},
                                        "next_obs":{"shape": obs_shape},
                                        "done":{}})

        for i in range(N):
            obs = np.full(obs_shape,i,dtype=np.double)
            act = np.full(act_dim,i,dtype=np.double)
            rew = i
            next_obs = obs + 1
            done = 0

            erb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        erb._encode_sample(range(buffer_size))

        erb.sample(32)

        erb.clear()

        self.assertEqual(erb.get_next_index(),0)
        self.assertEqual(erb.get_stored_size(),0)

    def test_add(self):
        buffer_size = 256
        obs_shape = (15,15)
        act_dim = 5

        rb = ReplayBuffer(buffer_size,{"obs":{"shape": obs_shape},
                                       "act":{"shape": act_dim},
                                       "rew":{},
                                       "next_obs": {"shape": obs_shape},
                                       "done": {}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        next_obs = obs + 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        self.assertEqual(rb.get_next_index(),1)
        self.assertEqual(rb.get_stored_size(),1)

        with self.assertRaises(KeyError):
            rb.add(obs=obs)

        self.assertEqual(rb.get_next_index(),1)
        self.assertEqual(rb.get_stored_size(),1)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        next_obs = np.stack((next_obs,next_obs))
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,next_obs=next_obs,done=done)

        self.assertEqual(rb.get_next_index(),3)
        self.assertEqual(rb.get_stored_size(),3)

    def test_default_dtype(self):
        buffer_size = 256

        rb = ReplayBuffer(buffer_size,{"done": {}},
                          default_dtype = np.float32)

        rb.add(done=1)
        self.assertEqual(rb.sample(1)["done"][0].dtype,np.float32)

    def test_multi_processing(self):
        buffer_size = 256

        rb = ReplayBuffer(buffer_size,{"obs": {"dtype": int}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        p = Process(target=add_args,args=[rb, [{"obs": i} for i in range(100)]])
        p.start()
        p.join()

        self.assertEqual(rb.get_next_index(),100)
        self.assertEqual(rb.get_stored_size(),100)

        s = rb.get_all_transitions()
        np.testing.assert_allclose(s["obs"].ravel(),np.arange(100,dtype=int))

    def test_multi_processing2(self):
        buffer_size = 256

        rb = ReplayBuffer(buffer_size,{"done": {}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        p = Process(target=add,args=[rb])
        q = Process(target=add,args=[rb])
        p.start()
        q.start()
        p.join()
        q.join()

        self.assertEqual(rb.get_next_index() ,200)
        self.assertEqual(rb.get_stored_size(),200)

    def test_multi_add_sample(self):
        buffer_size = 256

        rb = ReplayBuffer(buffer_size,{"done": {}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        p = Process(target=add,args=[rb])
        q = Process(target=add,args=[rb])
        r = Process(target=sample,args=[rb,32])
        p.start()
        p.join()

        q.start()
        r.start()
        q.join()
        r.join()

        self.assertEqual(rb.get_next_index() ,200)
        self.assertEqual(rb.get_stored_size(),200)

    def test_context(self):
        buffer_size = 256

        ctx = get_context("spawn")
        rb = ReplayBuffer(buffer_size, {"done": {}}, ctx=ctx)

        self.assertEqual(rb.get_next_index(), 0)
        self.assertEqual(rb.get_stored_size(), 0)

        p = Process(target=add, args=[rb])
        q = Process(target=add, args=[rb])
        r = Process(target=sample, args=[rb, 32])

        p.start()
        p.join()

        q.start()
        r.start()

        q.join()
        r.join()

        self.assertEqual(rb.get_next_index(), 200)
        self.assertEqual(rb.get_stored_size(), 200)

    @unittest.skipUnless(sys.version_info >= (3,8),
                         "SharedMemory is supported Python 3.8+")
    def test_backend(self):
        buffer_size = 256

        ctx = get_context("spawn")
        rb = ReplayBuffer(buffer_size, {"done": {}}, ctx=ctx, backend="SharedMemory")

        self.assertEqual(rb.get_next_index(), 0)
        self.assertEqual(rb.get_stored_size(), 0)

        p = Process(target=add, args=[rb])
        q = Process(target=add, args=[rb])
        r = Process(target=sample, args=[rb, 32])

        p.start()
        p.join()

        q.start()
        r.start()

        q.join()
        r.join()

        self.assertEqual(rb.get_next_index(), 200)
        self.assertEqual(rb.get_stored_size(), 200)

    def test_unknown_backend(self):
        with self.assertRaises(ValueError):
            ReplayBuffer(1, {"done": {}}, backend="UNKNOWN_BACKEND")


    def test_unstarted_manager(self):
        ReplayBuffer(10, {"done": {}}, ctx=SyncManager())

    def test_finished_manager(self):
        with SyncManager() as m:
            pass

        with self.assertRaises(ProcessError):
            ReplayBuffer(10, {"done": {}}, ctx=m)


class TestPrioritizedReplayBuffer(unittest.TestCase):
    def test_add(self):
        buffer_size = 500
        obs_shape = (84,84,3)
        act_dim = 10

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"shape": obs_shape},
                                                  "act": {"shape": act_dim},
                                                  "rew": {},
                                                  "done": {}})

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = 1.5

        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)

        self.assertAlmostEqual(rb.get_max_priority(),1.5)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = (0.2,0.4)
        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)


        rb.clear()
        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

    def test_context(self):
        buffer_size = 500
        obs_shape = (84,84,3)
        act_dim = 10

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"shape": obs_shape},
                                                  "act": {"shape": act_dim},
                                                  "rew": {},
                                                  "done": {}},
                                     ctx=get_context("spawn"))

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = 1.5

        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)

        self.assertAlmostEqual(rb.get_max_priority(),1.5)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = (0.2,0.4)
        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)


        rb.clear()
        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

    @unittest.skipUnless(sys.version_info >= (3,8),
                         "SharedMemory is supported Python 3.8+")
    def test_backend(self):
        buffer_size = 500
        obs_shape = (84,84,3)
        act_dim = 10

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"shape": obs_shape},
                                                  "act": {"shape": act_dim},
                                                  "rew": {},
                                                  "done": {}},
                                     backend="SharedMemory")

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = 1.5

        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)

        self.assertAlmostEqual(rb.get_max_priority(),1.5)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = (0.2,0.4)
        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)


        rb.clear()
        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

    def test_sample(self):
        buffer_size = 500
        obs_shape = (84,84,3)
        act_dim = 4

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"shape": obs_shape},
                                                  "act": {"shape": act_dim},
                                                  "rew": {},
                                                  "done": {}})

        obs = np.zeros(obs_shape)
        act = np.ones(act_dim)
        rew = 1
        done = 0

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = 1.5

        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)

        self.assertAlmostEqual(rb.get_max_priority(),1.5)

        obs = np.stack((obs,obs))
        act = np.stack((act,act))
        rew = (1,0)
        done = (0.0,1.0)

        rb.add(obs=obs,act=act,rew=rew,done=done)

        ps = (0.2,0.4)
        rb.add(obs=obs,act=act,rew=rew,done=done,priorities=ps)

        sample = rb.sample(64)

        w = sample["weights"]
        i = sample["indexes"]

        rb.update_priorities(i,w*w)

    def test_multi_processing(self):
        buffer_size = 256

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"dtype": int}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        p = Process(target=add_args,args=[rb,
                                          [{"obs": i, "priority": 0.5}
                                           for i in range(10)]])
        p.start()
        p.join()

        self.assertEqual(rb.get_next_index(),10)
        self.assertEqual(rb.get_stored_size(),10)

        s = rb.get_all_transitions()
        np.testing.assert_allclose(s["obs"].ravel(),np.arange(10,dtype=int))

    def test_mp_sample(self):
        buffer_size = 256
        add_size = 200
        one_hot = 3

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"dtype": int}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        p = Process(target=add_args,args=[rb,
                                          [{"obs": i,
                                            "priorities": 0 if i != one_hot else 1e+8}
                                           for i in range(add_size)]])
        p.start()
        p.join()

        self.assertEqual(rb.get_next_index(),add_size % buffer_size)
        self.assertEqual(rb.get_stored_size(),min(add_size,buffer_size))

        s = rb.sample(100,beta=1.0)

        self.assertTrue((s["obs"] >= 0).all())
        self.assertTrue((s["obs"] < add_size).all())

        u, counts = np.unique(s["obs"],return_counts=True)
        self.assertEqual(u[counts.argmax()],one_hot)


    def test_mp_update_priority(self):
        buffer_size = 256
        add_size = 200

        rb = PrioritizedReplayBuffer(buffer_size,{"obs": {"dtype": int}})

        self.assertEqual(rb.get_next_index(),0)
        self.assertEqual(rb.get_stored_size(),0)

        p = Process(target=add_args,args=[rb,
                                          [{"obs": i, "priorities": 0}
                                           for i in range(add_size)]])
        p.start()
        p.join()

        self.assertEqual(rb.get_next_index(),add_size % buffer_size)
        self.assertEqual(rb.get_stored_size(),min(add_size,buffer_size))

        s = rb.sample(1,beta=1.0)
        one_hot = s["indexes"][0]

        rb.update_priorities([one_hot],[1e+8])

        self.assertEqual(rb.get_next_index(),add_size % buffer_size)
        self.assertEqual(rb.get_stored_size(),min(add_size,buffer_size))


        s = rb.sample(100,beta=1.0)

        self.assertTrue((s["obs"] >= 0).all())
        self.assertTrue((s["obs"] < add_size).all())

        u, counts = np.unique(s["obs"],return_counts=True)
        self.assertEqual(u[counts.argmax()],one_hot)

    def test_float_size(self):
        rb = PrioritizedReplayBuffer(1e+2, {"done": {}})
        self.assertEqual(rb.get_buffer_size(), 100)

        m = get_context().Manager()
        rb  = PrioritizedReplayBuffer(1e+2, {"done": {}}, ctx=m)
        self.assertEqual(rb.get_buffer_size(), 100)
        m.shutdown()

    @unittest.skipUnless(sys.version_info >= (3,8),
                         "SharedMemory is supported Python 3.8+")
    def test_float_size_SharedMemory(self):
        rb = PrioritizedReplayBuffer(1e+2, {"done": {}}, backend="SharedMemory")
        self.assertEqual(rb.get_buffer_size(), 100)

        m = get_context().Manager()
        rb = PrioritizedReplayBuffer(1e+2, {"done": {}}, backend="SharedMemory",
                                     ctx=m)
        self.assertEqual(rb.get_buffer_size(), 100)
        m.shutdown()

    def test_unsampled_mask(self):
        rb = PrioritizedReplayBuffer(1, {"done": {}})
        rb.add(done=1.0)
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.sample(1)
        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 2.0)


        m = get_context().Manager()
        rb  = PrioritizedReplayBuffer(1, {"done": {}}, ctx=m)
        rb.add(done=1.0)
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.sample(1)
        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 2.0)

        m.shutdown()

    @unittest.skipUnless(sys.version_info >= (3,8),
                         "SharedMemory is supported Python 3.8+")
    def test_unsampled_mask_SharedMemory(self):
        rb = PrioritizedReplayBuffer(1, {"done": {}}, backend="SharedMemory")
        rb.add(done=1.0)
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.sample(1)
        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 2.0)


        m = get_context().Manager()
        rb  = PrioritizedReplayBuffer(1, {"done": {}}, ctx=m, backend="SharedMemory")
        rb.add(done=1.0)
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 1.0)

        rb.sample(1)
        rb.update_priorities([0], [2.0])
        self.assertEqual(rb.get_max_priority(), 2.0)

        m.shutdown()

    def test_unstarted_manager(self):
        PrioritizedReplayBuffer(10, {"done": {}}, ctx=SyncManager())

    def test_finished_manager(self):
        with SyncManager() as m:
            pass

        with self.assertRaises(ProcessError):
            PrioritizedReplayBuffer(10, {"done": {}}, ctx=m)

if __name__ == '__main__':
    unittest.main()
