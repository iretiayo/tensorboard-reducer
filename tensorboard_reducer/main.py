from argparse import ArgumentParser
from importlib.metadata import version
from typing import Dict, List, Optional, Sequence

from numpy.typing import ArrayLike as Array

from .io import load_tb_events, write_csv, write_tb_events


def reduce_events(
    events_dict: Dict[str, Array], reduce_ops: List[str]
) -> Dict[str, Dict[str, Array]]:
    """Perform numpy reduce ops on the last axis of each array
    in a dictionary of scalar TensorBoard event data. Each array enters
    this function with shape (n_timesteps, r_runs) and len(reduce_ops) exit
    with shape (n_timesteps,).

    Args:
        events_dict (dict[str, Array]): Dictionary of arrays to reduce.
        reduce_ops (list[str]): numpy reduce ops.

    Returns:
        dict[str, dict[str, Array]]: Dict of dicts where each subdict holds one reduced array
            for each of the specified reduce ops, e.g. {"loss": {"mean": arr.mean(-1),
            "std": arr.std(-1)}}.
    """

    reductions = {}

    for op in reduce_ops:

        reductions[op] = {}

        for tag, df in events_dict.items():

            reductions[op][tag] = getattr(df, op)(axis=1)

    return reductions


def main(argv: Optional[Sequence[str]] = None) -> int:

    parser = ArgumentParser("TensorBoard Reducer")

    parser.add_argument(
        "-i",
        "--indirs-glob",
        help=(
            "Glob pattern of the run directories to reduce. "
            "Remember to protect wildcards with quotes to prevent shell expansion."
        ),
    )
    parser.add_argument(
        "-o",
        "--outpath",
        help=(
            "File or directory where to save output on disk. Will save as a CSV file if path "
            "ends in '.csv' extension or else as TensorBoard run directories, one for each "
            "reduce op suffixed by the op's name, e.g. 'outpath-mean', 'outpath-max', etc."
            "If output format is CSV, the output file will have a two-level header containing "
            "one column for each combination of tag and reduce operation with tag name in "
            "first and reduce op in second level."
        ),
    )
    parser.add_argument(
        "-r",
        "--reduce-ops",
        type=lambda s: s.split(","),
        default=["mean"],
        help=(
            "Comma-separated names of numpy reduction ops (mean, std, min, max, ...). Default "
            "is mean. Each reduction is written to a separate output directory suffixed by op "
            "name. I.e. "
        ),
    )
    parser.add_argument(
        "-f",
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing reduction directories.",
    )
    parser.add_argument(
        "--lax-tags",
        action="store_false",
        help="Don't error if equal tags across different runs have unequal numbers of steps.",
    )
    parser.add_argument(
        "--lax-steps",
        action="store_false",
        help="Don't error if different runs have different sets of tags.",
    )

    tb_version = version("tensorboard_reducer")

    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {tb_version}"
    )
    args = parser.parse_args(argv)

    outpath, overwrite, reduce_ops = args.outpath, args.overwrite, args.reduce_ops

    events_dict = load_tb_events(
        args.indirs_glob, strict_tags=args.lax_tags, strict_steps=args.lax_steps
    )

    n_scalars = len(events_dict)

    if not args.lax_steps and not args.lax_tags:
        n_steps, n_events = list(events_dict.values())[0].shape

        print(
            f"Loaded {n_events} TensorBoard runs with {n_scalars} scalars "
            f"and {n_steps} steps each"
        )
        if n_scalars < 20:
            print(", ".join(events_dict.keys()))
    elif n_scalars < 20:
        print(
            "Loaded data for the following tags into arrays of shape (n_steps, n_runs):"
        )
        for tag, df in events_dict.items():
            print(f"- '{tag}': {df.shape}")

    reduced_events = reduce_events(events_dict, reduce_ops)

    if outpath.endswith(".csv"):

        write_csv(reduced_events, outpath, overwrite)

        print(f"Wrote '{reduce_ops}' reductions to '{outpath}'")

    else:

        write_tb_events(reduced_events, outpath, overwrite)

        for op in reduce_ops:
            print(f"Wrote '{op}' reduction to '{outpath}-{op}'")


if __name__ == "__main__":
    exit(main())
