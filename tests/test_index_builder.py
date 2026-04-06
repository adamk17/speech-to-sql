from rag.build_index import IndexBuilder


class TestIndexBuilder:
    def make_builder(self, chunk_size=5, chunk_overlap=2) -> IndexBuilder:
        return IndexBuilder(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def test_short_text_returns_single_chunk(self):
        builder = self.make_builder(chunk_size=10)
        result = builder._chunk_text("one two three")
        assert result == ["one two three"]

    def test_long_text_splits_into_chunks(self):
        builder = self.make_builder(chunk_size=3, chunk_overlap=1)
        words = "a b c d e f g"
        result = builder._chunk_text(words)
        assert len(result) > 1

    def test_chunks_have_correct_size(self):
        builder = self.make_builder(chunk_size=3, chunk_overlap=1)
        result = builder._chunk_text("a b c d e f g h i")
        for chunk in result[:-1]:
            assert len(chunk.split()) == 3

    def test_chunks_overlap(self):
        builder = self.make_builder(chunk_size=3, chunk_overlap=1)
        result = builder._chunk_text("a b c d e f")
        last_word_of_first = result[0].split()[-1]
        first_word_of_second = result[1].split()[0]
        assert last_word_of_first == first_word_of_second

    def test_text_exactly_chunk_size_returns_single_chunk(self):
        builder = self.make_builder(chunk_size=4)
        result = builder._chunk_text("a b c d")
        assert len(result) == 1
        assert result[0] == "a b c d"
