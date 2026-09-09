// A small JSON reader, enough for the files this repository publishes.
//
// The native tools read verify/vectors.json and data/snapshot-latest.json. Pulling a JSON
// library in for that would mean asking anyone who wants to check our numbers to first
// trust a dependency tree, which is the opposite of the point. Two hundred lines of
// recursive descent covers what we need: objects, arrays, strings, doubles, bools, null.
//
// C++17, standard library only.

#ifndef PREDLY_JSON_HPP
#define PREDLY_JSON_HPP

#include <cctype>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace predly {
namespace json {

class Value;
using Object = std::map<std::string, Value>;
using Array = std::vector<Value>;

enum class Type { Null, Bool, Number, String, Array, Object };

class Value {
public:
    Value() : type_(Type::Null) {}
    explicit Value(bool b) : type_(Type::Bool), bool_(b) {}
    explicit Value(double d) : type_(Type::Number), num_(d) {}
    explicit Value(std::string s) : type_(Type::String), str_(std::move(s)) {}
    explicit Value(Array a) : type_(Type::Array), arr_(std::move(a)) {}
    explicit Value(Object o) : type_(Type::Object), obj_(std::move(o)) {}

    Type type() const { return type_; }
    bool is_null() const { return type_ == Type::Null; }
    bool is_number() const { return type_ == Type::Number; }
    bool is_string() const { return type_ == Type::String; }
    bool is_array() const { return type_ == Type::Array; }
    bool is_object() const { return type_ == Type::Object; }

    double num() const {
        if (type_ != Type::Number) throw std::runtime_error("json: value is not a number");
        return num_;
    }
    bool boolean() const {
        if (type_ != Type::Bool) throw std::runtime_error("json: value is not a bool");
        return bool_;
    }
    const std::string& str() const {
        if (type_ != Type::String) throw std::runtime_error("json: value is not a string");
        return str_;
    }
    const Array& arr() const {
        if (type_ != Type::Array) throw std::runtime_error("json: value is not an array");
        return arr_;
    }
    const Object& obj() const {
        if (type_ != Type::Object) throw std::runtime_error("json: value is not an object");
        return obj_;
    }

    // Convenience lookups that do not throw on a missing key.
    const Value* find(const std::string& key) const {
        if (type_ != Type::Object) return nullptr;
        auto it = obj_.find(key);
        return it == obj_.end() ? nullptr : &it->second;
    }
    double num_or(const std::string& key, double fallback) const {
        const Value* v = find(key);
        return (v && v->is_number()) ? v->num() : fallback;
    }
    std::string str_or(const std::string& key, const std::string& fallback) const {
        const Value* v = find(key);
        return (v && v->is_string()) ? v->str() : fallback;
    }

private:
    Type type_;
    bool bool_ = false;
    double num_ = 0.0;
    std::string str_;
    Array arr_;
    Object obj_;
};

class Parser {
public:
    explicit Parser(const std::string& text) : s_(text) {}

    Value parse() {
        skip();
        Value v = value();
        skip();
        return v;
    }

private:
    const std::string& s_;
    std::size_t i_ = 0;

    [[noreturn]] void fail(const std::string& what) const {
        throw std::runtime_error("json: " + what + " at offset " + std::to_string(i_));
    }

    void skip() {
        while (i_ < s_.size() && (s_[i_] == ' ' || s_[i_] == '\t' || s_[i_] == '\n' || s_[i_] == '\r')) ++i_;
    }

    bool literal(const char* word) {
        const std::size_t n = std::char_traits<char>::length(word);
        if (s_.compare(i_, n, word) == 0) {
            i_ += n;
            return true;
        }
        return false;
    }

    Value value() {
        if (i_ >= s_.size()) fail("unexpected end of input");
        switch (s_[i_]) {
            case '{': return object();
            case '[': return array();
            case '"': return Value(string());
            case 't': if (literal("true")) return Value(true); fail("bad literal");
            case 'f': if (literal("false")) return Value(false); fail("bad literal");
            case 'n': if (literal("null")) return Value(); fail("bad literal");
            default: return Value(number());
        }
    }

    Value object() {
        Object out;
        ++i_;  // {
        skip();
        if (i_ < s_.size() && s_[i_] == '}') { ++i_; return Value(std::move(out)); }
        while (true) {
            skip();
            if (i_ >= s_.size() || s_[i_] != '"') fail("expected a key");
            std::string key = string();
            skip();
            if (i_ >= s_.size() || s_[i_] != ':') fail("expected a colon");
            ++i_;
            skip();
            out.emplace(std::move(key), value());
            skip();
            if (i_ < s_.size() && s_[i_] == ',') { ++i_; continue; }
            if (i_ < s_.size() && s_[i_] == '}') { ++i_; break; }
            fail("expected a comma or a closing brace");
        }
        return Value(std::move(out));
    }

    Value array() {
        Array out;
        ++i_;  // [
        skip();
        if (i_ < s_.size() && s_[i_] == ']') { ++i_; return Value(std::move(out)); }
        while (true) {
            skip();
            out.push_back(value());
            skip();
            if (i_ < s_.size() && s_[i_] == ',') { ++i_; continue; }
            if (i_ < s_.size() && s_[i_] == ']') { ++i_; break; }
            fail("expected a comma or a closing bracket");
        }
        return Value(std::move(out));
    }

    std::string string() {
        ++i_;  // opening quote
        std::string out;
        while (i_ < s_.size()) {
            const char c = s_[i_++];
            if (c == '"') return out;
            if (c != '\\') { out.push_back(c); continue; }
            if (i_ >= s_.size()) fail("unterminated escape");
            const char e = s_[i_++];
            switch (e) {
                case '"': out.push_back('"'); break;
                case '\\': out.push_back('\\'); break;
                case '/': out.push_back('/'); break;
                case 'b': out.push_back('\b'); break;
                case 'f': out.push_back('\f'); break;
                case 'n': out.push_back('\n'); break;
                case 'r': out.push_back('\r'); break;
                case 't': out.push_back('\t'); break;
                case 'u': {
                    // Keep it simple: decode the code point, emit UTF-8 for the basic plane.
                    if (i_ + 4 > s_.size()) fail("short unicode escape");
                    const unsigned cp = static_cast<unsigned>(std::strtoul(s_.substr(i_, 4).c_str(), nullptr, 16));
                    i_ += 4;
                    if (cp < 0x80) {
                        out.push_back(static_cast<char>(cp));
                    } else if (cp < 0x800) {
                        out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
                        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
                    } else {
                        out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
                        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
                        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
                    }
                    break;
                }
                default: fail("unknown escape");
            }
        }
        fail("unterminated string");
    }

    double number() {
        const std::size_t start = i_;
        if (i_ < s_.size() && (s_[i_] == '-' || s_[i_] == '+')) ++i_;
        while (i_ < s_.size() && (std::isdigit(static_cast<unsigned char>(s_[i_])) || s_[i_] == '.' ||
                                  s_[i_] == 'e' || s_[i_] == 'E' || s_[i_] == '-' || s_[i_] == '+')) {
            ++i_;
        }
        if (start == i_) fail("expected a number");
        return std::strtod(s_.substr(start, i_ - start).c_str(), nullptr);
    }
};

inline Value parse(const std::string& text) { return Parser(text).parse(); }

inline Value load(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("json: cannot open " + path);
    std::ostringstream ss;
    ss << in.rdbuf();
    return parse(ss.str());
}

}  // namespace json
}  // namespace predly

#endif  // PREDLY_JSON_HPP
