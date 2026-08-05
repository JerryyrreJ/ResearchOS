from collections import Counter
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from researchos.infrastructure.orm import (
    AssetRecord,
    AssetVersionRecord,
    FragmentRecord,
    IngestBatchRecord,
    IngestItemRecord,
    ParseRunRecord,
    RepresentationRecord,
    WorkspaceRecord,
)


@dataclass(frozen=True)
class StructuralGraph:
    assets: list[AssetRecord]
    versions: list[AssetVersionRecord]
    representations_by_version: dict[str, list[RepresentationRecord]]
    fragments_by_version: dict[str, int]


class OntologyQueryService:
    """Read-only projections over the deterministic M1 asset model.

    This service deliberately exposes provenance and version structure only. It
    does not infer semantic claims, classifications or research relations.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def require_workspace(self, workspace_id: str) -> WorkspaceRecord:
        workspace = self.session.get(WorkspaceRecord, workspace_id)
        if workspace is None:
            raise LookupError("workspace not found")
        return workspace

    def list_assets(self, workspace_id: str, query: str | None = None) -> list[AssetRecord]:
        self.require_workspace(workspace_id)
        statement = select(AssetRecord).where(AssetRecord.workspace_id == workspace_id)
        if query:
            statement = statement.where(AssetRecord.logical_name.ilike(f"%{query}%"))
        return list(
            self.session.scalars(
                statement.order_by(AssetRecord.created_at, AssetRecord.logical_name)
            )
        )

    def get_asset(self, asset_id: str) -> tuple[AssetRecord, list[AssetVersionRecord]]:
        asset = self.session.get(AssetRecord, asset_id)
        if asset is None:
            raise LookupError("object not found")
        versions = list(
            self.session.scalars(
                select(AssetVersionRecord)
                .where(AssetVersionRecord.asset_id == asset.id)
                .order_by(AssetVersionRecord.created_at)
            )
        )
        return asset, versions

    def build_graph(self, workspace_id: str) -> StructuralGraph:
        assets = self.list_assets(workspace_id)
        asset_ids = [asset.id for asset in assets]
        if not asset_ids:
            return StructuralGraph([], [], {}, {})

        versions = list(
            self.session.scalars(
                select(AssetVersionRecord)
                .where(AssetVersionRecord.asset_id.in_(asset_ids))
                .order_by(AssetVersionRecord.created_at)
            )
        )
        version_ids = [version.id for version in versions]
        representations = (
            list(
                self.session.scalars(
                    select(RepresentationRecord)
                    .where(RepresentationRecord.version_id.in_(version_ids))
                    .order_by(RepresentationRecord.created_at)
                )
            )
            if version_ids
            else []
        )
        fragments = (
            list(
                self.session.scalars(
                    select(FragmentRecord).where(FragmentRecord.version_id.in_(version_ids))
                )
            )
            if version_ids
            else []
        )
        representations_by_version: dict[str, list[RepresentationRecord]] = {}
        for representation in representations:
            representations_by_version.setdefault(representation.version_id, []).append(
                representation
            )
        fragments_by_version = dict(Counter(fragment.version_id for fragment in fragments))
        return StructuralGraph(
            assets=assets,
            versions=versions,
            representations_by_version=representations_by_version,
            fragments_by_version=fragments_by_version,
        )

    def project_state(self, workspace_id: str) -> dict[str, object]:
        self.require_workspace(workspace_id)
        assets = self.list_assets(workspace_id)
        asset_ids = [asset.id for asset in assets]
        versions = (
            list(
                self.session.scalars(
                    select(AssetVersionRecord).where(AssetVersionRecord.asset_id.in_(asset_ids))
                )
            )
            if asset_ids
            else []
        )
        version_ids = [version.id for version in versions]
        representations = (
            list(
                self.session.scalars(
                    select(RepresentationRecord).where(
                        RepresentationRecord.version_id.in_(version_ids)
                    )
                )
            )
            if version_ids
            else []
        )
        fragments = (
            list(
                self.session.scalars(
                    select(FragmentRecord).where(FragmentRecord.version_id.in_(version_ids))
                )
            )
            if version_ids
            else []
        )
        parse_runs = (
            list(
                self.session.scalars(
                    select(ParseRunRecord).where(ParseRunRecord.version_id.in_(version_ids))
                )
            )
            if version_ids
            else []
        )
        # Ingest item status counts are workspace-scoped through batches. The
        # query is kept separate from the asset projection so a failed item is
        # still visible even when it did not produce an asset.
        workspace_batches = list(
            self.session.scalars(
                select(IngestBatchRecord.id).where(IngestBatchRecord.workspace_id == workspace_id)
            )
        )
        ingest_items = (
            list(
                self.session.scalars(
                    select(IngestItemRecord).where(IngestItemRecord.batch_id.in_(workspace_batches))
                )
            )
            if workspace_batches
            else []
        )
        return {
            "asset_count": len(assets),
            "version_count": len(versions),
            "representation_count": len(representations),
            "fragment_count": len(fragments),
            "parse_run_counts": dict(Counter(run.status for run in parse_runs)),
            "ingest_item_counts": dict(Counter(item.status for item in ingest_items)),
        }
