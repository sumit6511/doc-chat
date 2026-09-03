from app.rag.chunker import chunk_text, normalize_whitespace, split_into_paragraphs, split_into_sentences


class TestNormalizeWhitespace:
    def test_collapses_internal_whitespace(self):
        assert normalize_whitespace("Hello    world\t\tfoo") == "Hello world foo"

    def test_collapses_excess_blank_lines(self):
        text = "Para one.\n\n\n\n\nPara two."
        assert normalize_whitespace(text) == "Para one.\n\nPara two."

    def test_empty_input(self):
        assert normalize_whitespace("") == ""
        assert normalize_whitespace("   \n\n  ") == ""


class TestParagraphAndSentenceSplitting:
    def test_split_into_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird."
        assert split_into_paragraphs(text) == ["First paragraph.", "Second paragraph.", "Third."]

    def test_split_into_sentences(self):
        sentences = split_into_sentences("First sentence. Second sentence! Third one?")
        assert sentences == ["First sentence.", "Second sentence!", "Third one?"]


class TestChunkText:
    def test_empty_input_returns_no_chunks(self):
        assert chunk_text("", chunk_size=800, chunk_overlap=100) == []
        assert chunk_text("   \n\n  ", chunk_size=800, chunk_overlap=100) == []

    def test_short_text_produces_single_chunk(self):
        chunks = chunk_text("This is a short sentence about RPC.", chunk_size=800, chunk_overlap=100)
        assert len(chunks) == 1
        assert chunks[0].content == "This is a short sentence about RPC."
        assert chunks[0].chunk_index == 0

    def test_long_text_splits_into_multiple_chunks(self):
        # 500 distinct three-word sentences => 1500 words, well past chunk_size=100.
        sentences = [f"Word{i} means something." for i in range(500)]
        text = " ".join(sentences)

        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)

        assert len(chunks) > 1
        for chunk in chunks:
            # Allow slack for the carried-over overlap plus one full sentence.
            assert chunk.word_count <= 100 + 20 + 3

    def test_multiple_paragraphs_are_each_represented(self):
        text = (
            "Distributed systems consist of independent components. "
            "They communicate over a network to achieve a common goal.\n\n"
            "Remote Procedure Call allows a client to invoke a remote procedure. "
            "It hides the network communication from the caller."
        )
        chunks = chunk_text(text, chunk_size=800, chunk_overlap=100)
        assert len(chunks) == 1  # fits comfortably under the word budget
        assert "Distributed systems" in chunks[0].content
        assert "Remote Procedure Call" in chunks[0].content

    def test_overlap_carries_words_into_the_next_chunk(self):
        sentences = [f"Sentence number {i} here." for i in range(40)]
        text = " ".join(sentences)

        chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)

        assert len(chunks) >= 2
        first_chunk_words = chunks[0].content.split()
        second_chunk_words = chunks[1].content.split()
        overlap_tail = first_chunk_words[-10:]
        assert overlap_tail == second_chunk_words[: len(overlap_tail)]

    def test_zero_overlap_produces_no_shared_words(self):
        # Globally unique tokens per sentence: with repeated vocabulary (e.g.
        # "Sentence number N here."), word *sets* would overlap across chunks
        # simply because "Sentence" appears everywhere — that would test
        # nothing. Unique tokens mean any shared word is genuine carryover.
        sentences = [f"UniqueToken{i}Alpha UniqueToken{i}Beta UniqueToken{i}Gamma." for i in range(40)]
        text = " ".join(sentences)

        chunks = chunk_text(text, chunk_size=50, chunk_overlap=0)

        assert len(chunks) >= 2
        first_chunk_words = set(chunks[0].content.split())
        second_chunk_words = set(chunks[1].content.split())
        assert first_chunk_words.isdisjoint(second_chunk_words)

    def test_single_sentence_longer_than_chunk_size_is_split(self):
        long_sentence = " ".join(f"word{i}" for i in range(300)) + "."
        chunks = chunk_text(long_sentence, chunk_size=100, chunk_overlap=10)
        assert len(chunks) >= 3

    def test_chunking_is_deterministic(self):
        text = " ".join(f"This is sentence {i}." for i in range(80))
        first = chunk_text(text, chunk_size=120, chunk_overlap=15)
        second = chunk_text(text, chunk_size=120, chunk_overlap=15)
        assert [c.content for c in first] == [c.content for c in second]

    def test_invalid_overlap_raises(self):
        import pytest

        with pytest.raises(ValueError):
            chunk_text("some text", chunk_size=100, chunk_overlap=100)
        with pytest.raises(ValueError):
            chunk_text("some text", chunk_size=100, chunk_overlap=-1)
