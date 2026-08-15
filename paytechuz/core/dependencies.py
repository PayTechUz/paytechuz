"""
Dependency checker for PayTechUZ integrations.
"""
import warnings
from typing import List


DEPENDENCIES = {
    'django': {
        'packages': ['django'],
        'install_cmd': 'pip install paytechuz[django]',
        'manual_install': 'pip install django',
    },
    'fastapi': {
        'packages': ['fastapi', 'sqlalchemy', 'pydantic'],
        'install_cmd': 'pip install paytechuz[fastapi]',
        'manual_install': (
            'pip install fastapi sqlalchemy pydantic python-multipart'
        ),
    },
}


class DependencyError(ImportError):
    """Raised when required dependencies are missing."""


def get_missing_dependencies(framework: str) -> List[str]:
    """
    Get the list of missing dependencies for a framework.

    Args:
        framework: Framework name ('django' or 'fastapi')

    Returns:
        List of missing package names
    """
    if framework not in DEPENDENCIES:
        raise ValueError(f"Unknown framework: {framework}")

    missing = []
    for package in DEPENDENCIES[framework]['packages']:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    return missing


def check_dependencies(framework: str, raise_error: bool = False) -> bool:
    """
    Check if dependencies for a specific framework are installed.

    Args:
        framework: Framework name ('django' or 'fastapi')
        raise_error: If True, raise DependencyError instead of warning

    Returns:
        bool: True if all dependencies are available

    Raises:
        DependencyError: If raise_error=True and dependencies are missing
    """
    missing_packages = get_missing_dependencies(framework)
    if not missing_packages:
        return True

    config = DEPENDENCIES[framework]
    error_msg = (
        f"\nPayTechUZ: missing dependencies for {framework.upper()}: "
        f"{', '.join(missing_packages)}\n"
        f"Install them with:\n"
        f"  {config['install_cmd']}\n"
        f"or manually:\n"
        f"  {config['manual_install']}\n"
    )

    if raise_error:
        raise DependencyError(error_msg)

    warnings.warn(error_msg, ImportWarning, stacklevel=2)
    return False


def require_framework(framework: str):
    """
    Decorator to check framework dependencies before function execution.

    Usage:
        @require_framework('django')
        def my_django_function():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            check_dependencies(framework, raise_error=True)
            return func(*args, **kwargs)
        return wrapper
    return decorator
