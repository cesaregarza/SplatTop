import asyncio
from functools import wraps
from typing import Awaitable, Callable, ParamSpec, TypeVar

from discord.ext import commands

T = TypeVar("T")
P = ParamSpec("P")

locks: dict[str, asyncio.Lock] = {}


def locked_check(
    locking_group: str,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """A decorator that provides a locking mechanism check for Discord commands.

    This decorator ensures that only one execution of the decorated command
    can occur at a time for a given locking_group. If the lock is already
    active, subsequent calls will be rejected.

    Args:
        locking_group (str): A string identifier for the lock group.

    Returns:
        Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
            A decorator that can be applied to a command.

    Example:
        @commands.command(name="my_command)
        @locked_check("my_lock_group")
        async def my_function(ctx: commands.Context, ...):
            # This command will be locked under "my_lock_group"
            ...
    """

    async def predicate(*args) -> bool:
        """The predicate for the command.

        Args:
            *args: Arguments for Discord compatibility (unused).

        Returns:
            bool: Whether the lock is available.
        """
        return (locking_group not in locks) or (
            not locks[locking_group].locked()
        )

    async def before_invoke(*args) -> None:
        """Function to be run before invocation.

        Args:
            *args: Arguments for Discord compatibility (unused).
        """
        if locking_group not in locks:
            locks[locking_group] = asyncio.Lock()
        await locks[locking_group].acquire()

    async def after_invoke(*args) -> None:
        """Function to be run after invocation.

        Args:
            *args: Arguments for Discord compatibility (unused).
        """
        locks[locking_group].release()

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        """The actual decorator applied to the function.

        Args:
            func (Callable[P, Awaitable[T]]): The async function to be
                decorated.

        Returns:
            Callable[P, Awaitable[T]]: The wrapped function.
        """
        return commands.check(predicate)(
            commands.before_invoke(before_invoke)(
                commands.after_invoke(after_invoke)(func)
            )
        )

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
