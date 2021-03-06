=====================================
Customizing Further a Regression Test
=====================================

In this section, we are going to show some more elaborate use cases of ReFrame.
Through the use of more advanced examples, we will demonstrate further customization options which modify the default options of the ReFrame pipeline.
The corresponding scripts as well as the source code of the examples discussed here can be found in the directory ``tutorial/advanced``.

Leveraging Makefiles
--------------------

We have already shown how you can compile a single source file associated with your regression test.
In this example, we show how ReFrame can leverage Makefiles to build executables.

Compiling a regression test through a Makefile is very straightforward with ReFrame.
If the :attr:`sourcepath <reframe.core.pipeline.RegressionTest.sourcepath>` attribute refers to a directory, then ReFrame will automatically invoke ``make`` there.

.. note:: More specifically, ReFrame constructs the final target source path as ``os.path.join(self.sourcesdir, self.sourcepath)``

By default, :attr:`sourcepath <reframe.core.pipeline.RegressionTest.sourcepath>` is the empty string and :attr:`sourcesdir <reframe.core.pipeline.RegressionTest.sourcesdir>` is set ``src/``.
As a result, by not specifying a :attr:`sourcepath <reframe.core.pipeline.RegressionTest.sourcepath>` at all, ReFrame will try to invoke ``make`` inside the ``src/`` directory of the test.
This is exactly what our first example here does.

For completeness, here are the contents of ``Makefile`` provided:

.. code-block:: makefile

  EXECUTABLE := advanced_example1

  OBJS := advanced_example1.o

  $(EXECUTABLE): $(OBJS)
      $(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

  $(OBJS): advanced_example1.c
      $(CC) $(CPPFLAGS) $(CFLAGS) -c $(LDFLAGS) -o $@ $^

The corresponding ``advanced_example1.c`` source file consists of a simple printing of a message, whose content depends on the preprocessor variable ``MESSAGE``:

.. code-block:: c

  #include <stdio.h>

  int main(){
  #ifdef MESSAGE
      char *message = "SUCCESS";
  #else
      char *message = "FAILURE";
  #endif
      printf("Setting of preprocessor variable: %s\n", message);
      return 0;
  }

The purpose of the regression test in this case is to set the preprocessor variable ``MESSAGE`` via ``CPPFLAGS`` and then check the standard output for the message ``SUCCESS``, which indicates that the preprocessor flag has been passed and processed correctly by the Makefile.

The contents of this regression test are the following (``tutorial/advanced/advanced_example1.py``):

.. code-block:: python

  import os

  import reframe.utility.sanity as sn
  from reframe.core.pipeline import RegressionTest


  class MakefileTest(RegressionTest):
      def __init__(self, **kwargs):
          super().__init__('preprocessor_check', os.path.dirname(__file__),
                           **kwargs)

          self.descr = ('ReFrame tutorial demonstrating the use of Makefiles '
                        'and compile options')
          self.valid_systems = ['*']
          self.valid_prog_environs = ['*']
          self.executable = './advanced_example1'
          self.sanity_patterns = sn.assert_found('SUCCESS', self.stdout)
          self.maintainers = ['put-your-name-here']
          self.tags = {'tutorial'}

      def compile(self):
          self.current_environ.cppflags = '-DMESSAGE'
          super().compile()


  def _get_checks(**kwargs):
      return [MakefileTest(**kwargs)]

The important bit here is the ``compile()`` method.

.. code-block:: python

  def compile(self):
      self.current_environ.cppflags = '-DMESSAGE'
      super().compile()

As in the simple single source file examples we showed in the `tutorial <tutorial.html>`__, we use the current programming environment's flags for modifying the compilation.
ReFrame will then compile the regression test source code as by invoking ``make`` as follows:

.. code-block:: bash

  make CC=cc CXX=CC FC=ftn CPPFLAGS=-DMESSAGE

Notice, how ReFrame passes all the programming environment's variables to the ``make`` invocation.
It is important to note here that, if a set of flags is set to :class:`None` (the default, if not otherwise set in the `ReFrame's configuration <configure.html#environments-configuration>`__), these are not passed to ``make``.
You can also completely disable the propagation of any flags to ``make`` by setting :attr:`self.propagate = False <reframe.core.environments.ProgEnvironment.propagate>` in your regression test.

At this point it is useful also to note that you can also use a custom Makefile, not named ``Makefile`` or after any other standard Makefile name.
In this case, you can pass the custom Makefile name as an argument to the compile method of the base :class:`RegressionTest <reframe.core.pipeline.RegressionTest>` class as follows:

.. code-block:: python

  super().compile(makefile='Makefile_custom')

Implementing a Run-Only Regression Test
---------------------------------------

There are cases when it is desirable to perform regression testing for an already built executable.
The following test uses the ``echo`` Bash shell command to print a random integer between specific lower and upper bounds.
Here is the full regression test (``tutorial/advanced/advanced_example2.py``):

.. code-block:: python

  import os

  import reframe.utility.sanity as sn
  from reframe.core.pipeline import RunOnlyRegressionTest


  class RunOnlyTest(RunOnlyRegressionTest):
      def __init__(self, **kwargs):
          super().__init__('run_only_check', os.path.dirname(__file__),
                           **kwargs)

          self.descr = ('ReFrame tutorial demonstrating the class'
                        'RunOnlyRegressionTest')
          self.valid_systems = ['*']
          self.valid_prog_environs = ['*']
          lower = 90
          upper = 100
          self.executable = 'echo $((RANDOM%({1}+1-{0})+{0}))'.format(
              lower, upper)
          self.sanity_patterns = sn.assert_bounded(sn.extractsingle(
              r'(?P<number>\S+)', self.stdout, 'number', float), lower, upper)

          self.maintainers = ['put-your-name-here']
          self.tags = {'tutorial'}


  def _get_checks(**kwargs):
      return [RunOnlyTest(**kwargs)]

There is nothing special for this test compared to those presented `earlier <tutorial.html>`__ except that it derives from the :class:`RunOnlyRegressionTest <reframe.core.pipeline.RunOnlyRegressionTest>`.
A thing to note about run-only regression tests is that the copying of their resources to the stage directory is performed at the beginning of the run phase.
For standard regression tests, this happens at the beginning of the compilation phase, instead.

Implementing a Compile-Only Regression Test
-------------------------------------------

ReFrame provides the option to write compile-only tests which consist only of a compilation phase without a specified executable.
This kind of tests must derive from the :class:`CompileOnlyRegressionTest <reframe.core.pipeline.CompileOnlyRegressionTest>` class provided by the framework.
The following example (``tutorial/advanced/advanced_example3.py``) reuses the code of our first example in this section and checks that no warnings are issued by the compiler:

.. code-block:: python

  import os

  import reframe.utility.sanity as sn
  from reframe.core.pipeline import CompileOnlyRegressionTest


  class CompileOnlyTest(CompileOnlyRegressionTest):
      def __init__(self, **kwargs):
          super().__init__('compile_only_check', os.path.dirname(__file__),
                           **kwargs)
          self.descr = ('ReFrame tutorial demonstrating the class'
                        'CompileOnlyRegressionTest')
          self.valid_systems = ['*']
          self.valid_prog_environs = ['*']
          self.sanity_patterns = sn.assert_not_found('warning', self.stderr)

          self.maintainers = ['put-your-name-here']
          self.tags = {'tutorial'}


  def _get_checks(**kwargs):
      return [CompileOnlyTest(**kwargs)]

The important thing to note here is that the standard output and standard error of the tests, accessible through the :attr:`stdout <reframe.core.pipeline.RegressionTest.stdout>` and :attr:`stderr <reframe.core.pipeline.RegressionTest.stderr>` attributes, are now the corresponding those of the compilation command.
So sanity checking can be done in exactly the same way as with a normal test.

Leveraging Environment Variables
--------------------------------

We have already demonstrated in the `tutorial <tutorial.html>`__ that ReFrame allows you to load the required modules for regression tests and also set any needed environment variables. When setting environment variables for your test through the :attr:`variables <reframe.core.pipeline.RegressionTest.variables>` attribute, you can assign them values of other, already defined, environment variables using the standard notation ``$OTHER_VARIABLE`` or ``${OTHER_VARIABLE}``.
The following regression test (``tutorial/advanced/advanced_example4.py``) sets the ``CUDA_HOME`` environment variable to the value of the ``CUDATOOLKIT_HOME`` and then compiles and runs a simple program:

.. code-block:: python

  import os

  import reframe.utility.sanity as sn
  from reframe.core.pipeline import RegressionTest


  class EnvironmentVariableTest(RegressionTest):
      def __init__(self, **kwargs):
          super().__init__('env_variable_check', os.path.dirname(__file__),
                           **kwargs)

          self.descr = ('ReFrame tutorial demonstrating the use'
                        'of environment variables provided by loaded modules')
          self.valid_systems = ['daint:gpu']
          self.valid_prog_environs = ['*']
          self.modules = ['cudatoolkit']
          self.variables = {'CUDA_HOME': '$CUDATOOLKIT_HOME'}
          self.executable = './advanced_example4'
          self.sanity_patterns = sn.assert_found(r'SUCCESS', self.stdout)
          self.maintainers = ['put-your-name-here']
          self.tags = {'tutorial'}

      def compile(self):
          super().compile(makefile='Makefile_example4')


  def _get_checks(**kwargs):
      return [EnvironmentVariableTest(**kwargs)]

Before discussing this test in more detail, let's first have a look in the source code and the Makefile of this example:

.. code-block:: cpp

  #include <stdio.h>
  #include <stdlib.h>
  #include <string.h>

  #ifndef CUDA_HOME
  #   define CUDA_HOME ""
  #endif

  int main() {
      char *cuda_home_compile = CUDA_HOME;
      char *cuda_home_runtime = getenv("CUDA_HOME");
      if (cuda_home_runtime &&
          strnlen(cuda_home_runtime, 256) &&
          strnlen(cuda_home_compile, 256) &&
          !strncmp(cuda_home_compile, cuda_home_runtime, 256)) {
          printf("SUCCESS\n");
      } else {
          printf("FAILURE\n");
          printf("Compiled with CUDA_HOME=%s, ran with CUDA_HOME=%s\n",
                 cuda_home_compile,
                 cuda_home_runtime ? cuda_home_runtime : "<null>");
      }

      return 0;
  }

This program is pretty basic, but enough to demonstrate the use of environment variables from ReFrame.
It simply compares the value of the ``CUDA_HOME`` macro with the value of the environment variable ``CUDA_HOME`` at runtime, printing ``SUCCESS`` if they are not empty and match.
The Makefile for this example compiles this source by simply setting ``CUDA_HOME`` to the value of the ``CUDA_HOME`` environment variable:

.. code-block:: makefile

  EXECUTABLE := advanced_example4

  CPPFLAGS = -DCUDA_HOME=\"$(CUDA_HOME)\"

  .SUFFIXES: .o .c

  OBJS := advanced_example4.o

  $(EXECUTABLE): $(OBJS)
      $(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

  $(OBJS): advanced_example4.c
      $(CC) $(CPPFLAGS) $(CFLAGS) -c $(LDFLAGS) -o $@ $^

  clean:
      /bin/rm -f $(OBJS) $(EXECUTABLE)

Coming back now to the ReFrame regression test, the ``CUDATOOLKIT_HOME`` environment variable is defined by the ``cudatoolkit`` module.
If you try to run the test, you will see that it will succeed, meaning that the ``CUDA_HOME`` variable was set correctly both during the compilation and the runtime.

When ReFrame `sets up <pipeline.html#the-setup-phase>`__ a test, it first loads its required modules and then sets the required environment variables expanding their values.
This has the result that ``CUDA_HOME`` takes the correct value in our example at the compilation time.

At runtime, ReFrame will generate the following instructions in the shell script associated with this test:

.. code-block:: bash

  module load cudatoolkit
  export CUDA_HOME=$CUDATOOLKIT_HOME

This ensures that the environment of the test is also set correctly at runtime.

Finally, as already mentioned `previously <#leveraging-makefiles>`__, since the ``Makefile`` name is not one of the standard ones, it has to be passed as an argument to the :func:`compile <reframe.core.pipeline.RegressionTest.compile>` method of the base :class:`RegressionTest <reframe.core.pipeline.RegressionTest>` class as follows:

.. code-block:: python

  super().compile(makefile='Makefile_example4')

Setting a Time Limit for Regression Tests
-----------------------------------------

ReFrame gives you the option to limit the execution time of regression tests.
The following example (``tutorial/advanced/advanced_example5.py``) demonstrates how you can achieve this by limiting the execution time of a test that tries to sleep 100 seconds:

.. code-block:: python

  import os

  import reframe.utility.sanity as sn
  from reframe.core.pipeline import RunOnlyRegressionTest


  class TimeLimitTest(RunOnlyRegressionTest):
      def __init__(self, **kwargs):
          super().__init__('time_limit_check', os.path.dirname(__file__),
                           **kwargs)

          self.descr = ('ReFrame tutorial demonstrating the use'
                        'of a user-defined time limit')
          self.valid_systems = ['daint:gpu', 'daint:mc']
          self.valid_prog_environs = ['*']
          self.time_limit = (0, 1, 0)
          self.executable = 'sleep'
          self.executable_opts = ['100']
          self.sanity_patterns = sn.assert_found(
              r'CANCELLED.*DUE TO TIME LIMIT', self.stderr)
          self.maintainers = ['put-your-name-here']
          self.tags = {'tutorial'}


  def _get_checks(**kwargs):
      return [TimeLimitTest(**kwargs)]

The important bit here is the following line that sets the time limit for the test to one minute:

.. code-block:: python

  self.time_limit = (0, 1, 0)

The :attr:`time_limit <reframe.core.pipeline.RegressionTest.time_limit>` attribute is a three-tuple in the form ``(HOURS, MINUTES, SECONDS)``.
Time limits are implemented for all the scheduler backends.

The sanity condition for this test verifies that associated job has been canceled due to the time limit.

.. code-block:: python

  self.sanity_patterns = sn.assert_found('CANCELLED.*TIME LIMIT', self.stderr)
