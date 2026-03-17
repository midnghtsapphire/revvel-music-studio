"""
Tests for engine.distribution module.

Covers metadata dataclasses, validate_track, and validate_release — all
pure-Python, deterministic, and requiring no external tools.
"""

import pytest

from engine.distribution import (
    TrackMetadata,
    ReleaseMetadata,
    validate_track,
    validate_release,
    generate_isrc,
    DISTRIBUTORS,
    DSPS,
)


# ---------------------------------------------------------------------------
# TrackMetadata tests
# ---------------------------------------------------------------------------

class TestTrackMetadata:
    def test_default_artist(self):
        track = TrackMetadata()
        assert track.artist == "Revvel"

    def test_default_genre(self):
        track = TrackMetadata()
        assert track.genre == "Alt Pop"

    def test_explicit_defaults_to_false(self):
        track = TrackMetadata()
        assert track.explicit is False

    def test_fields_can_be_set(self):
        track = TrackMetadata(title="Midnight", artist="Revvel", bpm=128.0)
        assert track.title == "Midnight"
        assert track.bpm == 128.0


# ---------------------------------------------------------------------------
# ReleaseMetadata tests
# ---------------------------------------------------------------------------

class TestReleaseMetadata:
    def test_default_release_type(self):
        release = ReleaseMetadata()
        assert release.release_type == "single"

    def test_default_tracks_is_empty_list(self):
        release = ReleaseMetadata()
        assert release.tracks == []

    def test_tracks_lists_are_independent(self):
        """Mutable default must not be shared between instances."""
        r1 = ReleaseMetadata()
        r2 = ReleaseMetadata()
        r1.tracks.append(TrackMetadata(title="Song"))
        assert len(r2.tracks) == 0


# ---------------------------------------------------------------------------
# validate_track tests
# ---------------------------------------------------------------------------

class TestValidateTrack:
    def _valid_track(self) -> TrackMetadata:
        return TrackMetadata(title="Neon Skies", artist="Revvel")

    def test_valid_track_has_no_errors(self):
        errors = validate_track(self._valid_track())
        assert errors == []

    def test_missing_title_is_an_error(self):
        track = self._valid_track()
        track.title = ""
        errors = validate_track(track)
        assert any("title" in e.lower() for e in errors)

    def test_missing_artist_is_an_error(self):
        track = self._valid_track()
        track.artist = ""
        errors = validate_track(track)
        assert any("artist" in e.lower() for e in errors)

    def test_title_over_200_chars_is_an_error(self):
        track = self._valid_track()
        track.title = "A" * 201
        errors = validate_track(track)
        assert any("200" in e for e in errors)

    def test_title_exactly_200_chars_is_valid(self):
        track = self._valid_track()
        track.title = "A" * 200
        errors = validate_track(track)
        assert not any("200" in e for e in errors)

    def test_title_with_leading_whitespace_is_an_error(self):
        track = self._valid_track()
        track.title = " Leading space"
        errors = validate_track(track)
        assert any("whitespace" in e.lower() for e in errors)

    def test_title_with_trailing_whitespace_is_an_error(self):
        track = self._valid_track()
        track.title = "Trailing space "
        errors = validate_track(track)
        assert any("whitespace" in e.lower() for e in errors)

    def test_returns_list(self):
        errors = validate_track(self._valid_track())
        assert isinstance(errors, list)


# ---------------------------------------------------------------------------
# validate_release tests
# ---------------------------------------------------------------------------

class TestValidateRelease:
    def _valid_track(self) -> TrackMetadata:
        return TrackMetadata(title="Neon Skies", artist="Revvel")

    def _valid_release(self) -> ReleaseMetadata:
        return ReleaseMetadata(
            title="Neon EP",
            artist="Revvel",
            release_type="single",
            tracks=[self._valid_track()],
        )

    def test_valid_release_has_no_errors(self):
        errors = validate_release(self._valid_release())
        assert errors == []

    def test_missing_title_is_an_error(self):
        release = self._valid_release()
        release.title = ""
        errors = validate_release(release)
        assert any("title" in e.lower() for e in errors)

    def test_missing_artist_is_an_error(self):
        release = self._valid_release()
        release.artist = ""
        errors = validate_release(release)
        assert any("artist" in e.lower() for e in errors)

    def test_no_tracks_is_an_error(self):
        release = self._valid_release()
        release.tracks = []
        errors = validate_release(release)
        assert any("track" in e.lower() for e in errors)

    def test_single_with_more_than_3_tracks_is_an_error(self):
        release = self._valid_release()
        release.release_type = "single"
        release.tracks = [self._valid_track() for _ in range(4)]
        errors = validate_release(release)
        assert any("single" in e.lower() for e in errors)

    def test_single_with_3_tracks_is_valid(self):
        release = self._valid_release()
        release.release_type = "single"
        release.tracks = [self._valid_track() for _ in range(3)]
        errors = validate_release(release)
        assert not any("single" in e.lower() for e in errors)

    def test_ep_with_fewer_than_2_tracks_is_an_error(self):
        release = self._valid_release()
        release.release_type = "ep"
        release.tracks = [self._valid_track()]
        errors = validate_release(release)
        assert any("ep" in e.lower() for e in errors)

    def test_ep_with_more_than_6_tracks_is_an_error(self):
        release = self._valid_release()
        release.release_type = "ep"
        release.tracks = [self._valid_track() for _ in range(7)]
        errors = validate_release(release)
        assert any("ep" in e.lower() for e in errors)

    def test_ep_with_4_tracks_is_valid(self):
        release = self._valid_release()
        release.release_type = "ep"
        release.tracks = [self._valid_track() for _ in range(4)]
        errors = validate_release(release)
        assert not any("ep" in e.lower() for e in errors)

    def test_nonexistent_artwork_path_is_an_error(self):
        release = self._valid_release()
        release.artwork_path = "/tmp/does_not_exist_xyz.jpg"
        errors = validate_release(release)
        assert any("artwork" in e.lower() or "not found" in e.lower() for e in errors)

    def test_track_errors_are_propagated(self):
        release = self._valid_release()
        release.tracks[0].title = ""  # invalid track
        errors = validate_release(release)
        assert any("Track 1" in e for e in errors)

    def test_returns_list(self):
        errors = validate_release(self._valid_release())
        assert isinstance(errors, list)


# ---------------------------------------------------------------------------
# generate_isrc tests
# ---------------------------------------------------------------------------

class TestGenerateIsrc:
    def test_returns_string(self):
        isrc = generate_isrc()
        assert isinstance(isrc, str)

    def test_starts_with_country_code(self):
        isrc = generate_isrc(country="US")
        assert isrc.startswith("US")

    def test_has_expected_length(self):
        # Format: CC-XXX-YY-NNNNN = 2+3+2+5 = 12 chars
        isrc = generate_isrc()
        assert len(isrc) == 12

    def test_custom_registrant(self):
        isrc = generate_isrc(registrant="HRS")
        assert "HRS" in isrc


# ---------------------------------------------------------------------------
# DISTRIBUTORS / DSPS constants tests
# ---------------------------------------------------------------------------

class TestConstants:
    def test_distributors_dict_is_not_empty(self):
        assert len(DISTRIBUTORS) > 0

    def test_each_distributor_has_required_keys(self):
        required = {"name", "audio_formats", "min_sample_rate", "artwork_formats"}
        for key, info in DISTRIBUTORS.items():
            missing = required - set(info.keys())
            assert not missing, f"Distributor '{key}' missing keys: {missing}"

    def test_dsps_list_is_not_empty(self):
        assert len(DSPS) > 0

    def test_spotify_is_in_dsps(self):
        assert "Spotify" in DSPS
