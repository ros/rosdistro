load("@rules_python//python:defs.bzl", _py_test = "py_test")

def py_pytest(name, srcs, deps=[], args=[], **kwargs):
    _py_test(
        name = name,
        main = "@rosdistro//bazel/python:pytest_main.py",
        srcs = srcs + ["@rosdistro//bazel/python:pytest_main.py"],
        deps = deps + ["@rosdistro//bazel/python:pytest"],
        args = args + ["$(location :%s)" % s for s in srcs],
        **kwargs,
    )