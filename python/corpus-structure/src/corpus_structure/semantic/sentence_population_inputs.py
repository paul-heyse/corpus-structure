"""Prepared CPU attachment of admitted sentence inventories and placement."""

from dataclasses import dataclass

from .data_operation_cpu import PopulationCPUInput
from .data_operation_partitions import (
    AcquiredPopulationPartition,
    PartitionCommitment,
    PartitionedInput,
)


@dataclass(frozen=True)
class SentencePopulationPlacement:
    commitment: PartitionCommitment
    group_digests: dict[str, str]


@dataclass(frozen=True)
class SentencePopulationInputs:
    placements: tuple[SentencePopulationPlacement, ...]
    packets: tuple[bytes, ...]

    def attach(self, header: bytes, populations) -> PartitionedInput:
        """Bind the received owned tables under their exact committed placement."""
        return PartitionedInput(
            header,
            self.packets,
            tuple(
                AcquiredPopulationPartition(placement.commitment, placement.group_digests, value)
                for placement, value in zip(self.placements, populations, strict=True)
            ),
        )


def prepare_sentence_populations(
    value: PartitionedInput, projection: str, *, groups: tuple[str, ...] = ()
) -> tuple[SentencePopulationInputs, tuple[PopulationCPUInput, ...]]:
    """Send the committed placement and only the columns the prepared consumer uses."""
    placements, inputs = [], []
    for part in value.populations:
        if groups:
            population = part.population.project_groups(groups)
            group_digests = {name: part.group_digests[name] for name in groups}
            from .data_operation_identity import canonical_identity

            digest = canonical_identity("partition-cpu-projection", group_digests).key
        else:
            population = part.population
            group_digests = dict(part.group_digests)
            digest = part.commitment.digest
        placements.append(SentencePopulationPlacement(part.commitment, group_digests))
        inputs.append(PopulationCPUInput(population, projection, digest))
    return SentencePopulationInputs(tuple(placements), value.packets), tuple(inputs)


def sentence_extent_blocks(value: PartitionedInput, commitment):
    """Materialize only the sentence rows needed by extent and context consumers."""
    from .sentence_partitions import (
        SentenceBlock,
        _verify_population_header,
        acquire_sentence_blocks,
    )

    if not value.populations:
        return acquire_sentence_blocks(value.packets, commitment)

    import pyarrow as pa
    import pyarrow.compute as pc

    from .data_operation_population import AcquiredPopulation

    _verify_population_header(value.populations, commitment)
    result = []
    for part in sorted(value.populations, key=lambda part: part.commitment.ordinal):
        placement, population = part.commitment, part.population
        sentence_rows = pc.call_function(
            "equal", [population.table["record_type"], pa.scalar("sentence")]
        )
        filtered = population.table.filter(sentence_rows)
        sentences = AcquiredPopulation._from_table(population.layout, filtered)
        result.append(
            SentenceBlock(
                placement.key,
                placement.ordinal,
                placement.start,
                placement.end,
                tuple(sentences.rows()),
            )
        )
    return tuple(result)
