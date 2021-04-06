from typing import Iterable

from jina.executors.dump import import_metas
from jina.executors.indexers.keyvalue import BinaryPbIndexer
from jina.executors.indexers.query import BaseQueryIndexer


class QueryBinaryPbIndexer(BinaryPbIndexer, BaseQueryIndexer):
    """A write-once Key-value indexer."""

    def __init__(self, dump_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if dump_path:
            self.load_dump(dump_path)
        else:
            self.logger.error(
                f'Dump path for {self.__class__} was None. No data to load for {self.__class__}'
            )

    def load_dump(self, path):
        """Load the dump at the path

        :param path: the path of the dump"""
        ids, metas = import_metas(path, str(self.pea_id))
        self.add(list(ids), list(metas))
        self.write_handler.flush()
        self.write_handler.close()
        self.handler_mutex = False
        self.is_handler_loaded = False
        del self.write_handler
        # warming up
        self.query('someid')
        # the indexer is write-once
        self.add = lambda *args, **kwargs: self.logger.warning(
            f'Index {self.index_abspath} is write-once'
        )

    def update(
        self, keys: Iterable[str], values: Iterable[bytes], *args, **kwargs
    ) -> None:
        """Disabled


        .. # noqa: DAR101
        """
        self.logger.warning(f'Index {self.index_abspath} is write-once')

    def delete(self, keys: Iterable[str], *args, **kwargs) -> None:
        """Disabled


        .. # noqa: DAR101
        """
        self.logger.warning(f'Index {self.index_abspath} is write-once')


class QueryKeyValueIndexer(QueryBinaryPbIndexer):
    """An alias"""
