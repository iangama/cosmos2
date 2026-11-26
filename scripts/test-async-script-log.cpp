#include <openspace/scripting/asyncscriptlog.h>
#include <cstdlib>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <mutex>
#include <vector>
using openspace::cosmos2log::AsyncScriptLog;
#define CHECK(value) do { if (!(value)) { std::cerr << "Failed at line " << __LINE__ << "\n"; std::abort(); } } while (false)
int main() {
    std::mutex mutex; std::condition_variable cv; bool entered = false, release = false, closed = false;
    std::vector<std::string> output; std::vector<std::string> errors;
    double submitMs = 0.;
    {
        AsyncScriptLog log([&](const std::optional<std::string>& line) {
            if (!line) { closed = true; return; }
            if (!entered) {
                std::unique_lock lock(mutex); entered = true; cv.notify_all();
                cv.wait(lock, [&]() { return release; });
            }
            output.push_back(*line);
        }, [&](const std::string& e) { errors.push_back(e); });
        CHECK(log.submit("first"));
        { std::unique_lock lock(mutex); cv.wait(lock, [&]() { return entered; }); }
        const auto start = std::chrono::steady_clock::now();
        for (int i = 0; i < 1000; ++i) { CHECK(log.submit(std::to_string(i))); }
        submitMs = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
        CHECK(submitMs < 100.); CHECK(log.status().written == 0);
        { std::lock_guard lock(mutex); release = true; } cv.notify_all();
    }
    CHECK(closed && errors.empty() && output.size() == 1001 && output.front() == "first");
    for (int i = 0; i < 1000; ++i) { CHECK(output[i + 1] == std::to_string(i)); }
    entered = release = closed = false; output.clear(); errors.clear();
    {
        AsyncScriptLog log([&](const std::optional<std::string>& line) {
            if (!line) { closed = true; return; }
            if (!entered) {
                std::unique_lock lock(mutex); entered = true; cv.notify_all();
                cv.wait(lock, [&]() { return release; });
            }
            output.push_back(*line);
        }, [&](const std::string& e) { errors.push_back(e); }, 4);
        CHECK(log.submit("one"));
        { std::unique_lock lock(mutex); cv.wait(lock, [&]() { return entered; }); }
        CHECK(log.submit("two")); CHECK(!log.submit("too big")); CHECK(!log.submit("tri"));
        CHECK(log.status().queuedBytes == 3 && log.status().dropped == 2);
        { std::lock_guard lock(mutex); release = true; } cv.notify_all();
    }
    CHECK(closed && output == std::vector<std::string>({"one", "two"}) && !errors.empty());
    entered = release = false;
    {
        AsyncScriptLog log([&](const std::optional<std::string>& line) {
            if (!line) { return; }
            if (!entered) {
                std::unique_lock lock(mutex); entered = true; cv.notify_all();
                cv.wait(lock, [&]() { return release; });
            }
        }, [&](const std::string&) {});
        CHECK(log.submit("hold"));
        { std::unique_lock lock(mutex); cv.wait(lock, [&]() { return entered; }); }
        for (int i = 0; i < 1024; ++i) { CHECK(log.submit("")); }
        CHECK(!log.submit("")); CHECK(log.status().dropped == 1);
        { std::lock_guard lock(mutex); release = true; } cv.notify_all();
    }
    errors.clear(); closed = false;
    {
        AsyncScriptLog log([&](const std::optional<std::string>& line) {
            if (!line) { closed = true; return; } throw std::runtime_error("injected I/O failure");
        }, [&](const std::string& e) { errors.push_back(e); });
        CHECK(log.submit("entry"));
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!log.status().failed && std::chrono::steady_clock::now() < deadline) { std::this_thread::yield(); }
        CHECK(log.status().failed && log.status().dropped == 1 && !log.submit("after failure"));
    }
    CHECK(closed && !errors.empty());
    std::cout << "{\"ordered_entries\":1001,\"blocked_sink_submit_ms\":" << submitMs
              << ",\"shutdown_drains_and_closes\":true,\"bounded_overflow_explicit\":true,\"IO_failure_explicit\":true,\"zero_length_entries_also_bounded\":true}\n";
}
