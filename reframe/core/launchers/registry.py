import reframe.core.fields as fields


# Name registry for job launchers
_LAUNCHERS = {}


def register_launcher(name, local=False):
    """Class decorator for registering new job launchers.

    :arg name: The registration name of this launcher
    :arg local: :class:`True` if launcher may only submit local jobs,
        :class:`False` otherwise.

    .. note::
       .. versionadded:: 2.8

       This method is only relevant to developers of new job launchers.
    """
    def _register_launcher(cls):
        if name in _LAUNCHERS:
            raise ReframeError(
                "a job launcher is already registered with name '%s'" % name)

        cls.is_local = fields.ConstantField(bool(local))
        cls.registered_name = fields.ConstantField(name)
        _LAUNCHERS[name] = cls
        return cls

    return _register_launcher


def getlauncher(name):
    """Get launcher by its registered name.

    The available names are those specified in the
    :doc:`configuration file </configure>`.

    This method may become handy in very special situations, e.g., testing an
    application that needs to replace the system partition launcher or if a
    different launcher must be used for a different programming environment.

    For example, if you want to replace the current partition's launcher with
    the local one, here is how you can achieve it:

    ::

        def setup(self, partition, environ, **job_opts):
            super().setup(partition, environ, **job_opts)
            self.job.launcher = getlauncher('local')()


    Note that this method returns a launcher class type and not an instance of
    that class.
    You have to instantiate it explicitly before assigning it to the
    :attr:`launcher` attribute of the job.

    :arg name: The name of the launcher to retrieve.
    :returns: The class of the launcher requested, which is a subclass of
        :class:`reframe.core.launchers.JobLauncher`.

    .. note::
       .. versionadded:: 2.8
    """
    try:
        return _LAUNCHERS[name]
    except KeyError:
        raise ConfigurationError("no such job launcher: '%s'" % name)


# Import the launchers modules to trigger their registration
import reframe.core.launchers.local
import reframe.core.launchers.mpi
