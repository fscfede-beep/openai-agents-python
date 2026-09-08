        wrapper: RunContextWrapper[Any] | None = None,
    ) -> None:
        """Run compaction using responses.compact API.

        When a run context is provided, the billed compaction request contributes to
        that run's usage totals.
        """
        # Reject a caller-supplied retained chain if a destructive mutation completed
        # while this call was waiting to acquire compaction ownership. Input-mode compaction
        # does not depend on the retained Responses chain; it reads post-mutation history after
        # acquiring the lock, so it must remain eligible.
        pre_lock_invalidation_generation = self._response_chain_invalidation_generation
        pre_lock_mutation_generation = self._mutation_generation
        async with self._mutation_lock:
            if pre_lock_invalidation_generation != self._response_chain_invalidation_generation:
                guard_response_id = (
                    args.get("response_id") if args and args.get("response_id") else self._response_id
                )
                guard_store = args.get("store") if args and "store" in args else None
                guard_requested_mode = args.get("compaction_mode") if args else None
                guard_mode = self._resolve_compaction_mode_for_response(
                    response_id=guard_response_id,
                    store=guard_store,
                    requested_mode=guard_requested_mode,
                )
                if guard_mode == "previous_response_id":
                    logger.debug("skip: response chain invalidated while waiting for mutation lock")
                    return
            has_expected_generation = wrapper is not None and hasattr(
                wrapper, "_session_compaction_generation"
            )
            expected_generation = (
                getattr(wrapper, "_session_compaction_generation", None)
                if has_expected_generation
                else None
            )
            if has_expected_generation and (
                not isinstance(expected_generation, int)
                or expected_generation != self._mutation_generation
            ):
                logger.warning(
                    "Skipped compaction because Session history changed after this "
                    "run appended its items."
                )
                return
            if (
                not has_expected_generation
                and pre_lock_mutation_generation != self._mutation_generation
            ):
                guard_response_id = (
                    args.get("response_id")
                    if args and args.get("response_id")
                    else self._response_id
                )
                guard_store = args.get("store") if args and "store" in args else None
                guard_requested_mode = args.get("compaction_mode") if args else None
                guard_mode = self._resolve_compaction_mode_for_response(
                    response_id=guard_response_id,
                    store=guard_store,
                    requested_mode=guard_requested_mode,
                )
                if guard_mode == "previous_response_id":
                    self._invalidate_response_chain()
                    logger.warning(