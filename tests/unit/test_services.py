"""
Unit tests for service container and dependency injection.

Tests the ServiceContainer registration, resolution, and lifecycle
management including thread safety and global container operations.
"""
import pytest
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod

from src.services import (
    ServiceContainer,
    get_container,
    reset_container,
    AudioProcessorInterface,
    TranscriberInterface,
    SummarizerInterface,
    FFmpegAudioProcessor,
    ReplicateTranscriberService,
    LLMSummarizer,
    register_default_services,
)


# Mock implementations for testing
class MockAudioProcessor(AudioProcessorInterface):
    """Mock audio processor for testing."""

    def probe(self, input_path):
        return "mock probe output"

    def normalize_loudness(self, input_path, output_path):
        pass

    def extract_audio(self, input_path, output_path, codec=None):
        pass

    def get_duration(self, input_path):
        return 180.0


class MockTranscriber(TranscriberInterface):
    """Mock transcriber for testing."""

    def transcribe(self, audio_path, progress_callback=None):
        return {"segments": []}

    def get_segments(self, audio_path, progress_callback=None):
        return []


class MockSummarizer(SummarizerInterface):
    """Mock summarizer for testing."""

    def summarize_transcript(self, segments, template=None):
        return "mock summary"

    def summarize_with_cod(self, text, passes=2):
        return "mock cod summary"

    @property
    def provider_name(self):
        return "mock"


@pytest.fixture
def container():
    """Create a fresh ServiceContainer for each test."""
    return ServiceContainer()


@pytest.fixture(autouse=True)
def reset_global_container():
    """Reset global container before each test."""
    reset_container()
    yield
    reset_container()


def test_register_and_resolve_singleton(container):
    """Test that singleton registration returns same instance on multiple resolves."""
    container.register(AudioProcessorInterface, MockAudioProcessor, singleton=True)

    instance1 = container.resolve(AudioProcessorInterface)
    instance2 = container.resolve(AudioProcessorInterface)

    assert instance1 is instance2
    assert isinstance(instance1, MockAudioProcessor)


def test_register_and_resolve_factory(container):
    """Test that factory registration returns different instances on each resolve."""
    container.register(AudioProcessorInterface, MockAudioProcessor, singleton=False)

    instance1 = container.resolve(AudioProcessorInterface)
    instance2 = container.resolve(AudioProcessorInterface)

    assert instance1 is not instance2
    assert isinstance(instance1, MockAudioProcessor)
    assert isinstance(instance2, MockAudioProcessor)


def test_register_instance(container):
    """Test that register_instance returns exact same object."""
    pre_created = MockAudioProcessor()
    container.register_instance(AudioProcessorInterface, pre_created)

    resolved = container.resolve(AudioProcessorInterface)

    assert resolved is pre_created


def test_resolve_unregistered_raises(container):
    """Test that resolving unregistered interface raises KeyError."""
    with pytest.raises(KeyError) as exc_info:
        container.resolve(AudioProcessorInterface)

    assert "AudioProcessorInterface" in str(exc_info.value)


def test_reset_clears_all(container):
    """Test that reset clears all registrations."""
    container.register(AudioProcessorInterface, MockAudioProcessor)
    container.register_instance(TranscriberInterface, MockTranscriber())
    container.register_factory(SummarizerInterface, MockSummarizer)

    container.reset()

    with pytest.raises(KeyError):
        container.resolve(AudioProcessorInterface)
    with pytest.raises(KeyError):
        container.resolve(TranscriberInterface)
    with pytest.raises(KeyError):
        container.resolve(SummarizerInterface)


def test_is_registered(container):
    """Test is_registered returns correct status."""
    assert not container.is_registered(AudioProcessorInterface)

    container.register(AudioProcessorInterface, MockAudioProcessor)
    assert container.is_registered(AudioProcessorInterface)

    container.reset()
    assert not container.is_registered(AudioProcessorInterface)


def test_get_audio_processor(container):
    """Test get_audio_processor convenience method."""
    container.register(AudioProcessorInterface, MockAudioProcessor)

    processor = container.get_audio_processor()

    assert isinstance(processor, MockAudioProcessor)
    assert isinstance(processor, AudioProcessorInterface)


def test_get_transcriber(container):
    """Test get_transcriber convenience method."""
    container.register(TranscriberInterface, MockTranscriber)

    transcriber = container.get_transcriber()

    assert isinstance(transcriber, MockTranscriber)
    assert isinstance(transcriber, TranscriberInterface)


def test_get_summarizer(container):
    """Test get_summarizer convenience method."""
    container.register(SummarizerInterface, MockSummarizer)

    summarizer = container.get_summarizer()

    assert isinstance(summarizer, MockSummarizer)
    assert isinstance(summarizer, SummarizerInterface)


def test_register_default_services():
    """Test register_default_services registers all three interfaces."""
    reset_container()
    register_default_services()

    container = get_container()

    assert container.is_registered(AudioProcessorInterface)
    assert container.is_registered(TranscriberInterface)
    assert container.is_registered(SummarizerInterface)

    # Verify they can be resolved
    processor = container.get_audio_processor()
    transcriber = container.get_transcriber()
    summarizer = container.get_summarizer()

    assert isinstance(processor, FFmpegAudioProcessor)
    assert isinstance(transcriber, ReplicateTranscriberService)
    assert isinstance(summarizer, LLMSummarizer)


def test_register_default_services_idempotent():
    """Test register_default_services can be called multiple times safely."""
    reset_container()
    register_default_services()

    container = get_container()
    first_processor = container.get_audio_processor()
    first_transcriber = container.get_transcriber()
    first_summarizer = container.get_summarizer()

    # Call again - should not error
    register_default_services()

    # Should get same instances (singletons)
    second_processor = container.get_audio_processor()
    second_transcriber = container.get_transcriber()
    second_summarizer = container.get_summarizer()

    assert first_processor is second_processor
    assert first_transcriber is second_transcriber
    assert first_summarizer is second_summarizer


def test_thread_safety_singleton(container):
    """Test that singleton resolution is thread-safe and returns same instance."""
    container.register(AudioProcessorInterface, MockAudioProcessor, singleton=True)

    instances = []

    def resolve_service():
        instance = container.resolve(AudioProcessorInterface)
        instances.append(instance)
        return instance

    # Resolve concurrently from multiple threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(resolve_service) for _ in range(20)]
        results = [f.result() for f in futures]

    # All resolved instances should be the same object
    first_instance = instances[0]
    for instance in instances:
        assert instance is first_instance

    # Verify we only created one instance
    assert len(set(id(i) for i in instances)) == 1


def test_global_container():
    """Test get_container returns ServiceContainer instance."""
    container = get_container()

    assert isinstance(container, ServiceContainer)


def test_reset_container():
    """Test reset_container creates new empty container."""
    container1 = get_container()
    container1.register(AudioProcessorInterface, MockAudioProcessor)

    assert container1.is_registered(AudioProcessorInterface)

    reset_container()
    container2 = get_container()

    # Should be a new container instance
    assert container2 is not container1
    # Should be empty
    assert not container2.is_registered(AudioProcessorInterface)


def test_ffmpeg_audio_processor_construction():
    """Test FFmpegAudioProcessor instantiates without error."""
    processor = FFmpegAudioProcessor()

    assert isinstance(processor, AudioProcessorInterface)
    assert hasattr(processor, 'probe')
    assert hasattr(processor, 'normalize_loudness')
    assert hasattr(processor, 'extract_audio')
    assert hasattr(processor, 'get_duration')


def test_register_factory_callable(container):
    """Test register_factory with custom factory callable."""
    call_count = 0

    def custom_factory():
        nonlocal call_count
        call_count += 1
        return MockAudioProcessor()

    container.register_factory(AudioProcessorInterface, custom_factory)

    instance1 = container.resolve(AudioProcessorInterface)
    instance2 = container.resolve(AudioProcessorInterface)

    assert call_count == 2
    assert instance1 is not instance2


def test_multiple_interface_registration(container):
    """Test registering multiple interfaces in same container."""
    container.register(AudioProcessorInterface, MockAudioProcessor)
    container.register(TranscriberInterface, MockTranscriber)
    container.register(SummarizerInterface, MockSummarizer)

    processor = container.resolve(AudioProcessorInterface)
    transcriber = container.resolve(TranscriberInterface)
    summarizer = container.resolve(SummarizerInterface)

    assert isinstance(processor, MockAudioProcessor)
    assert isinstance(transcriber, MockTranscriber)
    assert isinstance(summarizer, MockSummarizer)


def test_singleton_created_only_once(container):
    """Test that singleton implementation is constructed only once."""

    class CountingProcessor(AudioProcessorInterface):
        instances_created = 0

        def __init__(self):
            CountingProcessor.instances_created += 1

        def probe(self, input_path):
            return "probe"

        def normalize_loudness(self, input_path, output_path):
            pass

        def extract_audio(self, input_path, output_path, codec=None):
            pass

        def get_duration(self, input_path):
            return 0.0

    CountingProcessor.instances_created = 0
    container.register(AudioProcessorInterface, CountingProcessor, singleton=True)

    # Resolve multiple times
    instance1 = container.resolve(AudioProcessorInterface)
    instance2 = container.resolve(AudioProcessorInterface)
    instance3 = container.resolve(AudioProcessorInterface)

    assert CountingProcessor.instances_created == 1
    assert instance1 is instance2 is instance3


def test_container_independence():
    """Test that separate container instances are independent."""
    container1 = ServiceContainer()
    container2 = ServiceContainer()

    container1.register(AudioProcessorInterface, MockAudioProcessor)

    assert container1.is_registered(AudioProcessorInterface)
    assert not container2.is_registered(AudioProcessorInterface)

    # container2 should raise KeyError
    with pytest.raises(KeyError):
        container2.resolve(AudioProcessorInterface)


def test_resolve_with_mixed_registration_types(container):
    """Test resolve works correctly with mixed registration types."""
    # Singleton registration
    container.register(AudioProcessorInterface, MockAudioProcessor, singleton=True)

    # Instance registration
    pre_created = MockTranscriber()
    container.register_instance(TranscriberInterface, pre_created)

    # Factory registration
    container.register_factory(SummarizerInterface, MockSummarizer)

    # All should resolve correctly
    processor1 = container.resolve(AudioProcessorInterface)
    processor2 = container.resolve(AudioProcessorInterface)
    assert processor1 is processor2

    transcriber = container.resolve(TranscriberInterface)
    assert transcriber is pre_created

    summarizer1 = container.resolve(SummarizerInterface)
    summarizer2 = container.resolve(SummarizerInterface)
    assert summarizer1 is not summarizer2
