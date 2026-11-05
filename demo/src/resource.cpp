#include <memory>
int resource_safe(void) {
    auto sample = std::make_unique<int>(42);
    return *sample;
}
