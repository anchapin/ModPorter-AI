import os
import pytest
from pathlib import Path
# Attempt to import ModPorterConversionCrew, adjust path as needed
try:
    from ai_engine.src.crew.conversion_crew import ModPorterConversionCrew
except ImportError:
    # Fallback for different project structures or test environments
    # This might need adjustment based on how Python path is configured
    from src.crew.conversion_crew import ModPorterConversionCrew


# (Keep MODS_TO_TEST and compare_addons as they are)
MODS_TO_TEST = [
    ("vein_miner", "conversion_test_mods/vein_miner/veinminer.jar", "conversion_test_mods/vein_miner/veinminer_downloaded.mcaddon"),
    ("mowzies_mobs", "conversion_test_mods/mowzies_mobs/mowzies_mobs.jar", "conversion_test_mods/mowzies_mobs/mowzies_mobs_downloaded.mcaddon"),
    ("tinkers_construct", "conversion_test_mods/tinkers_construct/tinkers_construct.jar", "conversion_test_mods/tinkers_construct/tinkers_construct_downloaded.mcaddon"),
]

def run_modporter_ai(java_mod_path: str, output_dir: str) -> str | None:
    """
    Runs the ModPorter-AI tool to convert a Java mod to a Bedrock addon.
    This function now attempts to use the actual ModPorterConversionCrew.
    """
    print(f"Attempting to run actual ModPorter-AI conversion for: {java_mod_path}")
    print(f"Output directory: {output_dir}")

    # Ensure MOCK_AI_RESPONSES is set to true if not already set,
    # to avoid actual LLM calls during this phase of testing.
    # This can be refined later if live LLM testing is needed for these specific tests.
    original_mock_env = os.environ.get("MOCK_AI_RESPONSES")
    os.environ["MOCK_AI_RESPONSES"] = "true"

    # Ensure OPENAI_API_KEY is set to a dummy value if MOCK_AI_RESPONSES is true,
    # as some initialization paths might still check for its presence.
    original_api_key_env = os.environ.get("OPENAI_API_KEY")
    if os.environ.get("MOCK_AI_RESPONSES", "false").lower() == "true":
        os.environ["OPENAI_API_KEY"] = "dummy_key_for_mock_testing"

    try:
        conversion_crew = ModPorterConversionCrew() # Add constructor arguments if needed

        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        print(f"Calling conversion_crew.convert_mod with mod_path='{java_mod_path}', output_path='{output_dir}'")
        conversion_result = conversion_crew.convert_mod(
            mod_path=Path(java_mod_path),
            output_path=Path(output_dir)
            # Add other parameters like smart_assumptions if needed, defaults are True
        )

        print(f"ModPorter-AI conversion result: {conversion_result}")

        if conversion_result and conversion_result.get('status') == 'completed':
            # Find the generated .mcaddon file
            # The PackagingAgent is responsible for creating this.
            # We need to know the naming convention or search for it.
            # Based on PackagingAgent's potential behavior, it might be named after the mod or a UUID.
            # For now, let's assume it's the only .mcaddon file in the output_dir.
            for file in os.listdir(output_dir):
                if file.endswith(".mcaddon"):
                    generated_addon_path = os.path.join(output_dir, file)
                    print(f"Found generated addon: {generated_addon_path}")
                    return generated_addon_path
            print(f"No .mcaddon file found in {output_dir} after successful conversion.")
            return None
        else:
            print(f"ModPorter-AI conversion did not complete successfully: {conversion_result.get('status') if conversion_result else 'No result'}")
            error_message = conversion_result.get('error', 'Unknown error') if conversion_result else 'Unknown error'
            detailed_report_logs = conversion_result.get('detailed_report', {}).get('logs', []) if conversion_result else []
            print(f"Error: {error_message}")
            print(f"Detailed logs: {detailed_report_logs}")
            return None

    except Exception as e:
        print(f"An error occurred while running ModPorter-AI: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Restore original environment variables
        if original_mock_env is None:
            del os.environ["MOCK_AI_RESPONSES"]
        else:
            os.environ["MOCK_AI_RESPONSES"] = original_mock_env

        if original_api_key_env is None:
            if "OPENAI_API_KEY" in os.environ: # Check if it was set by us
                 del os.environ["OPENAI_API_KEY"]
        else:
            os.environ["OPENAI_API_KEY"] = original_api_key_env


def compare_addons(generated_addon_path, downloaded_addon_path, tolerance=0.2):
    """
    Compares the file size of two addon files and checks if the
    difference is within a given tolerance.
    """
    if not os.path.exists(generated_addon_path):
        pytest.fail(f"Generated addon file not found: {generated_addon_path}")
    if not os.path.exists(downloaded_addon_path):
        pytest.fail(f"Downloaded addon file not found: {downloaded_addon_path}")

    generated_size = os.path.getsize(generated_addon_path)
    downloaded_size = os.path.getsize(downloaded_addon_path)

    difference = abs(generated_size - downloaded_size)
    average_size = (generated_size + downloaded_size) / 2

    if average_size == 0:
        # Both files are empty, so they are the same
        percentage_difference = 0
    else:
        percentage_difference = difference / average_size

    print(f"Generated Addon Size: {generated_size} bytes")
    print(f"Downloaded Addon Size: {downloaded_size} bytes")
    print(f"Percentage Difference: {percentage_difference:.2%}")

    if percentage_difference > tolerance:
        print(f"Test Failed: File size difference ({percentage_difference:.2%}) is greater than the tolerance of {tolerance:.2%}")
        return False
    else:
        print("Test Passed: File size difference is within tolerance.")
        return True

@pytest.mark.parametrize("mod_name, java_mod_fixture, downloaded_addon_fixture", MODS_TO_TEST)
def test_mod_conversion_comparison(mod_name, java_mod_fixture, downloaded_addon_fixture, tmp_path, request):
    """
    Tests the ModPorter-AI conversion by comparing its output
    with a known downloaded Bedrock addon.
    """
    # Construct full paths to fixture files
    fixtures_dir = os.path.join(os.path.dirname(request.fspath), '..', 'fixtures')

    java_mod_path = os.path.join(fixtures_dir, java_mod_fixture)
    downloaded_addon_path = os.path.join(fixtures_dir, downloaded_addon_fixture)

    # Define the output directory for ModPorter-AI within the test's temporary directory
    output_directory = tmp_path / f"{mod_name}_output"
    # output_directory.mkdir() # The run_modporter_ai function now creates this

    print(f"\nTesting mod: {mod_name}")
    print(f"Java mod path: {java_mod_path}")
    print(f"Downloaded addon path: {downloaded_addon_path}")
    print(f"Output directory: {output_directory}")

    # --- Execution ---
    print("Starting ModPorter-AI conversion...")
    generated_addon = run_modporter_ai(java_mod_path, str(output_directory))

    assert generated_addon is not None, f"ModPorter-AI failed to produce an output file for {mod_name}."
    assert os.path.exists(generated_addon), f"ModPorter-AI output file not found: {generated_addon}"

    print(f"Conversion successful. Generated addon at: {generated_addon}")
    
    assert compare_addons(generated_addon, downloaded_addon_path), \
        f"Addon comparison failed for {mod_name}. File size difference exceeded tolerance."
