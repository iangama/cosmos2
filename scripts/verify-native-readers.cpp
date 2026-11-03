// Independent native checks for the local font/galaxy startup adaptations.
#include <modules/galaxy/rendering/galaxypointreader.h>
#include <ghoul/font/utf8.h>
#include <array>
#include <bit>
#include <chrono>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#ifdef _WIN32
#include <windows.h>
#endif

void require(bool condition) {
    if (!condition) { throw std::runtime_error("Native reader verification failed"); }
}

int main(int argc, char** argv) {
    try {
        using ghoul::fontrendering::decodeFontUtf8;
        require(decodeFontUtf8("Via L\xC3\xA1" "ctea \xE2\x80\x94").at(5) == 0xE1);
        require(decodeFontUtf8("\xCE\xB2").at(0) == 0x3B2);
        require(decodeFontUtf8("\xE2" "a").at(1) == 'a');
        require(decodeFontUtf8("\xC0\xAF").at(0) == 0xFFFD);
        require(decodeFontUtf8("\xED\xA0\x80").at(0) == 0xFFFD);
        require(decodeFontUtf8("\xF4\x90\x80\x80").at(0) == 0xFFFD);
        require(decodeFontUtf8("\xF0\x9F\x8C\x8C").size() == 1);
        if (sizeof(wchar_t) == 2) {
            require(decodeFontUtf8("\xF0\x9F\x8C\x8C").at(0) == 0xFFFD);
        }
        size_t unicodeCompared = 0;
#ifdef _WIN32
        // Windows' Unicode conversion is independent of the renderer decoder.
        for (wchar_t scalar = 1; scalar != 0xFFFF; ++scalar) {
            if (scalar >= 0xD800 && scalar <= 0xDFFF) { continue; }
            char bytes[4];
            const int count = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS,
                &scalar, 1, bytes, 4, nullptr, nullptr);
            require(count > 0);
            const auto decoded = decodeFontUtf8(std::string_view(bytes, count));
            require(decoded.size() == 1 && decoded.front() == scalar);
            ++unicodeCompared;
        }
#endif
        std::array<float, 7> values;
        for (const auto bad : {"", "0 0 0 0 0 0", "0 0 0 0 0 0 0 extra",
            "nan 0 0 0 0 0 0", "inf 0 0 0 0 0 0", "1e100 0 0 0 0 0 0",
            "+-1 0 0 0 0 0 0", "1,2 0 0 0 0 0 0", "1x 0 0 0 0 0 0"})
        {
            require(!openspace::parseGalaxyPoint(bad, values));
        }
        require(openspace::parseGalaxyPoint(" +1.0\t-2e-3 0 4 5 6 7\r", values));
        require(values[0] == 1.f && values[1] == -0.002f && values[6] == 7.f);
        for (const auto text : {"0 0 0 0 0 0 0\r\n1 2 3 4 5 6 7\n",
            "0 0 0 0 0 0 0\n1 2 3 4 5 6 7"})
        {
            std::istringstream rows(text);
            size_t consumed = 0;
            require(openspace::readGalaxyPointRows(rows, 2,
                [&](const auto&) { ++consumed; }));
            require(consumed == 2);
        }
        std::istringstream truncated("0 0 0 0 0 0 0\n");
        require(!openspace::readGalaxyPointRows(truncated, 2, [](const auto&) {}));
        // A legal whitespace prefix crosses a bulk-read boundary.
        std::istringstream crossBoundary(std::string(1024 * 1024 - 5, ' ') +
            "1 2 3 4 5 6 7\n");
        require(openspace::readGalaxyPointRows(crossBoundary, 1,
            [](const auto& row) { require(row[6] == 7.f); }));
        if (argc != 2) { throw std::runtime_error("Supply the original galaxy COFF path"); }
        std::ifstream source(argv[1], std::ios::binary);
        require(source.good());
        std::string line;
        std::getline(source, line);
        require(line == "COFF");
        std::getline(source, line);
        const size_t declared = std::stoull(line);
        size_t rows = 0, differences = 0;
        std::vector<std::array<float, 7>> upstreamRows;
        upstreamRows.reserve(declared);
        double referenceTime = 0., optimizedTime = 0.;
        while (rows < declared && std::getline(source, line)) {
            std::array<float, 7> reference;
            auto began = std::chrono::steady_clock::now();
            std::istringstream upstream(line);
            for (float& value : reference) { upstream >> value; }
            require(static_cast<bool>(upstream));
            upstreamRows.push_back(reference);
            referenceTime += std::chrono::duration<double>(
                std::chrono::steady_clock::now() - began).count();
            began = std::chrono::steady_clock::now();
            require(openspace::parseGalaxyPoint(line, values));
            optimizedTime += std::chrono::duration<double>(
                std::chrono::steady_clock::now() - began).count();
            for (size_t j = 0; j < 7; j++) {
                differences += std::bit_cast<uint32_t>(reference[j]) !=
                    std::bit_cast<uint32_t>(values[j]);
            }
            ++rows;
        }
        require(rows == declared && differences == 0);
        source.clear(); source.seekg(0);
        std::getline(source, line); std::getline(source, line);
        size_t bulkRows = 0;
        const auto bulkBegan = std::chrono::steady_clock::now();
        require(openspace::readGalaxyPointRows(source, declared,
            [&](const auto& row) {
                for (size_t j = 0; j < 7; j++) {
                    require(std::bit_cast<uint32_t>(upstreamRows.at(bulkRows)[j]) ==
                        std::bit_cast<uint32_t>(row[j]));
                }
                ++bulkRows;
            }));
        require(bulkRows == declared);
        const double bulkTime = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - bulkBegan).count();
        std::cout << "{\"rows\":" << rows << ",\"float_values\":" << rows * 7
            << ",\"bit_differences\":" << differences
            << ",\"bmp_scalars_compared_to_windows\":" << unicodeCompared
            << ",\"reference_parse_s\":" << referenceTime
            << ",\"optimized_parse_s\":" << optimizedTime
            << ",\"bulk_read_and_compare_s\":" << bulkTime
            << ",\"scope\":\"Native parsing and Unicode checks; not renderer FPS\"}\n";
    }
    catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
