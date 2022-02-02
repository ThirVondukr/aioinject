from aioinject import Module, providers, Container


def test_can_create_module():
    assert Module()


def test_should_copy_providers_in_namespace_to_attribute():
    class TestModule(Module):
        a = providers.Callable(int)

    assert TestModule.providers == [TestModule.a]


def test_should_not_copy_other_namespace_members():
    class TestModule(Module):
        a = int
        b = providers.Provider
        c = Module
        d = Module()

    assert TestModule.providers == []


def test_modules_dont_share_same_providers_list():
    class TestModule(Module):
        pass

    assert TestModule.providers is not Module.providers


def test_modules_share_same_provider_instances():
    class TestModule(Module):
        a = providers.Callable(int)

    class ChildModule(TestModule):
        pass

    assert ChildModule.providers[0] is TestModule.providers[0]


def test_mount():
    class TestModule(Module):
        a = providers.Callable(int)

    container = Container()
    container.mount(TestModule)

    assert container.providers == {int: [TestModule.a]}
