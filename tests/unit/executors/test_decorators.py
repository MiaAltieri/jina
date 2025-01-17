import os

import numpy as np
import pytest
from jina.executors.decorators import (
    as_update_method,
    as_train_method,
    as_ndarray,
    batching,
    require_train,
    store_init_kwargs,
    single,
)


def test_as_update_method():
    class A:
        def __init__(self):
            self.is_updated = False

        @as_update_method
        def f(self):
            pass

    a = A()
    assert not a.is_updated
    a.f()
    assert a.is_updated


def test_as_train_method():
    class A:
        def __init__(self):
            self.is_trained = False

        @as_train_method
        def f(self):
            pass

    a = A()
    assert not a.is_trained
    a.f()
    assert a.is_trained


def test_as_ndarray():
    class A:
        @as_ndarray
        def f_list(self, *args, **kwargs):
            return [0]

        @as_ndarray
        def f_int(self, *args, **kwargs):
            return 0

    a = A()

    assert isinstance(a.f_list(), np.ndarray)
    with pytest.raises(TypeError):
        a.f_int()


def test_require_train():
    class A:
        def __init__(self):
            self.is_trained = False

        @require_train
        def f(self):
            pass

    a = A()
    a.is_trained = False
    with pytest.raises(RuntimeError):
        a.f()
    a.is_trained = True
    a.f()


def test_store_init_kwargs():
    class A:
        @store_init_kwargs
        def __init__(self, a, b, c, *args, **kwargs):
            pass

        @store_init_kwargs
        def f(self, a, b, *args, **kwargs):
            pass

    instance = A('a', 'b', c=5, d='d')
    assert instance._init_kwargs_dict
    assert instance._init_kwargs_dict == {'a': 'a', 'b': 'b', 'c': 5}

    with pytest.raises(TypeError):
        instance.f('a', 'b', c='c')


def test_single():
    class A:
        def __init__(self):
            self.call_nbr = 0

        @single
        def f(self, data):
            assert isinstance(data, int)
            self.call_nbr += 1
            return data

    instance = A()
    result = instance.f([1, 1, 1, 1])
    assert result == [1, 1, 1, 1]
    assert instance.call_nbr == 4

    result = instance.f(1)
    assert result == 1


def test_single_kwargs_call():
    class A:
        @single
        def f(self, data):
            assert isinstance(data, int)
            return data

    instance = A()
    result = instance.f(data=1)
    assert result == 1


def test_single_np_ndarray():
    class A:
        def __init__(self):
            self.call_nbr = 0

        @single
        def f(self, data):
            assert isinstance(data, np.ndarray)
            assert data.shape == (5,)
            self.call_nbr += 1
            return data

    instance = A()
    input_np = np.random.random((4, 5))
    result = instance.f(input_np)
    np.testing.assert_equal(result, input_np)
    assert instance.call_nbr == 4


def test_single_np_ndarray_kwargs_call():
    class A:
        @single
        def f(self, data):
            assert isinstance(data, np.ndarray)
            assert data.shape == (5,)
            return data

    instance = A()
    input_np = np.random.random(5)
    result = instance.f(data=input_np)
    np.testing.assert_equal(result, input_np)


def test_single_string():
    class A:
        def __init__(self):
            self.call_nbr = 0

        @single
        def f(self, data):
            assert isinstance(data, str)
            return data

    instance = A()
    result = instance.f(['test0', 'test1'])
    assert len(result) == 2
    for i, res in enumerate(result):
        assert res == f'test{i}'

    result = instance.f('test0')
    assert result == 'test0'


def test_single_bytes():
    class A:
        def __init__(self):
            self.call_nbr = 0

        @single
        def f(self, data):
            assert isinstance(data, bytes)
            return data

    instance = A()
    result = instance.f([str.encode('test0'), str.encode('test1')])
    assert len(result) == 2
    for i, res in enumerate(result):
        assert res == str.encode(f'test{i}')

    result = instance.f(b'test0')
    assert result == b'test0'


def test_batching():
    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.batch_sizes = []

        @batching
        def f(self, data):
            self.batch_sizes.append(len(data))
            return data

    instance = A(1)
    result = instance.f([1, 1, 1, 1])
    assert result == [1, 1, 1, 1]
    assert len(instance.batch_sizes) == 4
    for batch_size in instance.batch_sizes:
        assert batch_size == 1

    instance = A(3)
    result = instance.f([1, 1, 1, 1])
    assert result == [1, 1, 1, 1]
    assert len(instance.batch_sizes) == 2
    assert instance.batch_sizes[0] == 3
    assert instance.batch_sizes[1] == 1

    instance = A(5)
    result = instance.f([1, 1, 1, 1])
    assert result == [1, 1, 1, 1]
    assert len(instance.batch_sizes) == 1
    assert instance.batch_sizes[0] == 4


@pytest.mark.parametrize('input_shape', [(4, 5), (4, 5, 5)])
def test_batching_np_array(input_shape):
    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.batch_sizes = []

        @batching
        def f(self, data):
            self.batch_sizes.append(len(data))
            return data

    instance = A(1)
    input_np = np.random.random(input_shape)
    result = instance.f(input_np)
    np.testing.assert_equal(result, input_np)
    assert len(instance.batch_sizes) == 4
    for batch_size in instance.batch_sizes:
        assert batch_size == 1

    instance = A(3)
    result = instance.f(input_np)
    np.testing.assert_equal(result, input_np)
    assert len(instance.batch_sizes) == 2
    assert instance.batch_sizes[0] == 3
    assert instance.batch_sizes[1] == 1

    instance = A(5)
    result = instance.f(input_np)
    np.testing.assert_equal(result, input_np)
    assert len(instance.batch_sizes) == 1
    assert instance.batch_sizes[0] == 4


def test_batching_slice_on():
    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.batch_sizes = []

        @batching(slice_on=2)
        def f(self, key, data):
            self.batch_sizes.append(len(data))
            return data

    instance = A(1)
    result = instance.f(None, [1, 1, 1, 1])
    assert result == [1, 1, 1, 1]
    assert len(instance.batch_sizes) == 4
    for batch_size in instance.batch_sizes:
        assert batch_size == 1

    instance = A(3)
    result = instance.f(None, [1, 1, 1, 1])
    assert result == [1, 1, 1, 1]
    assert len(instance.batch_sizes) == 2
    assert instance.batch_sizes[0] == 3
    assert instance.batch_sizes[1] == 1

    instance = A(5)
    result = instance.f(None, [1, 1, 1, 1])
    assert result == [1, 1, 1, 1]
    assert len(instance.batch_sizes) == 1
    assert instance.batch_sizes[0] == 4


def test_batching_memmap(tmpdir):
    path = os.path.join(str(tmpdir), 'vec.gz')
    vec = np.random.random([10, 10])
    with open(path, 'wb') as f:
        f.write(vec.tobytes())

    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size

        @batching
        def f(self, data):
            assert data.shape == (2, 10)
            return data

    instance = A(2)
    result = instance.f(
        np.memmap(path, dtype=vec.dtype.name, mode='r', shape=vec.shape)
    )
    assert result.shape == (10, 10)
    assert isinstance(result, np.ndarray)


def test_batching_ordinal_idx_arg(tmpdir):
    path = os.path.join(str(tmpdir), 'vec.gz')
    vec = np.random.random([10, 10])
    with open(path, 'wb') as f:
        f.write(vec.tobytes())

    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.ord_idx = []

        @batching(ordinal_idx_arg=2)
        def f(self, data, ord_idx):
            self.ord_idx.append(ord_idx)
            return list(range(ord_idx.start, ord_idx.stop))

    instance = A(2)
    result = instance.f(
        np.memmap(path, dtype=vec.dtype.name, mode='r', shape=vec.shape),
        slice(0, vec.shape[0]),
    )
    assert len(instance.ord_idx) == 5
    assert instance.ord_idx[0].start == 0
    assert instance.ord_idx[0].stop == 2
    assert instance.ord_idx[1].start == 2
    assert instance.ord_idx[1].stop == 4
    assert instance.ord_idx[2].start == 4
    assert instance.ord_idx[2].stop == 6
    assert instance.ord_idx[3].start == 6
    assert instance.ord_idx[3].stop == 8
    assert instance.ord_idx[4].start == 8
    assert instance.ord_idx[4].stop == 10

    assert result == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.skip(
    reason='Currently wrong implementation of batching with labels, not well considered in batching helper'
)
def test_batching_with_label():
    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size

        @batching(label_on=2)
        def f(self, data, labels):
            return data, labels

    instance = A(2)
    data = [1, 1, 2, 2]
    labels = ['label1', 'label1', 'label2', 'label2']
    result = instance.f(data, labels)
    assert result == [[(1, 'label1'), (1, 'label1')], [(2, 'label2'), (2, 'label2')]]


def test_batching_multi():
    slice_nargs = 3

    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.batching = []

        @batching(slice_nargs=slice_nargs)
        def f(self, *datas):
            assert len(datas) == slice_nargs
            d0, d1, d2 = datas
            assert d0.shape == (2, 2)
            assert d1.shape == (2, 4)
            assert d2.shape == (2, 6)
            concat = np.concatenate(datas, axis=1)
            self.batching.append(concat)
            return concat

    num_docs = 4
    batch_size = 2
    instance = A(batch_size)
    data0 = np.random.rand(num_docs, 2)
    data1 = np.random.rand(num_docs, 4)
    data2 = np.random.rand(num_docs, 6)
    data = [data0, data1, data2]
    result = instance.f(*data)
    from math import ceil

    result_dim = sum([d.shape[1] for d in data])
    assert result.shape == (num_docs, result_dim)
    assert len(instance.batching) == ceil(num_docs / batch_size)
    for batch in instance.batching:
        assert batch.shape == (batch_size, result_dim)


def test_single_multi():
    class A:
        def __init__(self):
            self.call_nbr = 0

        @single(slice_nargs=3)
        def f(self, data0, data1, data2):
            assert isinstance(data0, int)
            assert isinstance(data1, int)
            assert isinstance(data2, int)
            self.call_nbr += 1
            return data1

    instance = A()
    data0 = [0, 0, 0, 0]
    data1 = [1, 1, 1, 1]
    data2 = [2, 2, 2, 2]
    data = [data0, data1, data2]
    result = instance.f(*data)
    assert result == [1, 1, 1, 1]
    assert instance.call_nbr == 4

    instance = A()
    result = instance.f(0, 1, 2)
    assert result == 1


def test_batching_as_ndarray():
    class A:
        def __init__(self, batch_size):
            self.batch_size = batch_size
            self.batch_sizes = []

        @as_ndarray
        @batching
        def f(self, data):
            self.batch_sizes.append(len(data))
            return data

    instance = A(1)
    input_data = [[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]]
    result = instance.f(input_data)
    assert isinstance(result, np.ndarray)
    np.testing.assert_equal(result, np.array(input_data))
    assert len(instance.batch_sizes) == 4
    for batch_size in instance.batch_sizes:
        assert batch_size == 1

    instance = A(3)
    result = instance.f(input_data)
    assert isinstance(result, np.ndarray)
    np.testing.assert_equal(result, np.array(input_data))
    assert len(instance.batch_sizes) == 2
    assert instance.batch_sizes[0] == 3
    assert instance.batch_sizes[1] == 1

    instance = A(5)
    result = instance.f(input_data)
    assert isinstance(result, np.ndarray)
    np.testing.assert_equal(result, np.array(input_data))
    assert len(instance.batch_sizes) == 1
    assert instance.batch_sizes[0] == 4


def test_single_slice_on():
    class A:
        @single(slice_on=2)
        def f(self, key, data, *args, **kwargs):
            assert isinstance(data, int)
            return data

    instance = A()
    result = instance.f(None, [1, 1, 1, 1])
    assert result == [1, 1, 1, 1]


def test_single_multi_input_slice_on():
    class A:
        @single(slice_on=1, slice_nargs=2)
        def f(self, key, data, *args, **kwargs):
            assert isinstance(data, int)
            assert isinstance(key, str)
            return data

    instance = A()
    data = instance.f(['a', 'b', 'c', 'd'], [1, 1, 1, 1])
    assert isinstance(data, list)
    assert data == [1, 1, 1, 1]


@pytest.mark.parametrize('slice_on, num_data', [(1, 3), (2, 2)])
def test_single_multi_input_slice_on_error(slice_on, num_data):
    class A:
        @single(slice_on=slice_on, slice_nargs=num_data)
        def f(self, key, data, *args, **kwargs):
            assert isinstance(data, int)
            assert isinstance(key, str)
            return data

    instance = A()
    with pytest.raises(IndexError):
        instance.f(['a', 'b', 'c', 'd'], [1, 1, 1, 1])


def test_single_multi_input_kwargs_call():
    class A:
        @single
        def f(self, key, data, *args, **kwargs):
            assert isinstance(data, int)
            assert isinstance(key, str)
            return data

    instance = A()
    result = instance.f(data=1, key='a')
    assert result == 1
