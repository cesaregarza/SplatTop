import asyncio
from functools import wraps
from typing import Awaitable, Callable, ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")

locks: dict[str, asyncio.Lock] = {}


def locked_function(
    locking_group: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """A decorator that provides a locking mechanism for asynchronous functions.

    This decorator ensures that only one execution of the decorated function
    can occur at a time for a given locking_group. If the lock is already
    active, subsequent calls will be rejected.

    Args:
        locking_group (str): A string identifier for the lock group.

    Returns:
        Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
            A decorator function.

    Example:
        @lock("my_lock_group")
        async def my_function():
            # This function will be locked under "my_lock_group"
            ...
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        """The actual decorator applied to the function.

        Args:
            func (Callable[P, Awaitable[T]]): The async function to be
                decorated.

        Returns:
            Callable[P, Awaitable[T]]: The wrapped function.
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """The wrapper function that applies the locking mechanism.

            Args:
                *args: Positional arguments to pass to the decorated function.
                **kwargs: Keyword arguments to pass to the decorated function.

            Returns:
                T: The return value of the decorated function.

            Raises:
                RuntimeError: If the lock is already active.
            """
            if locking_group not in locks:
                locks[locking_group] = asyncio.Lock()

            if locks[locking_group].locked():
                raise RuntimeError(
                    f"Lock for '{locking_group}' is already active. Function "
                    "execution rejected."
                )

            async with locks[locking_group]:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def extract_from_message(message: str, tag: str) -> str:
    """Given a message and a tag, extract the value associated with the tag.

    For example, given the following message:
    ```
    <tag1>value1</tag1>
    <tag2>value2</tag2>
    ```

    Calling `extract_from_message(message, "tag1")` would return
    `"value1"`, and calling `extract_from_message(message, "tag2")`
    would return `"value2"`.

    Args:
        message (str): The message to extract the value from.
        tag (str): The tag to extract the value for.

    Returns:
        str: The extracted value.
    """
    start_tag = f"<{tag}>"
    end_tag = f"</{tag}>"

    return message.split(start_tag)[1].split(end_tag)[0].strip()
