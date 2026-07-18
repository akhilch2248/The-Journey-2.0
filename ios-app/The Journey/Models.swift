//
//  Models.swift
//  The Journey
//
//  API data transfer objects, mirrored from backend/app/schemas.
//

import Foundation

struct TokenResponse: Codable, Sendable {
    let accessToken: String
    let tokenType: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
    }
}

struct UserProfile: Codable, Sendable {
    let id: Int
    let provider: String
    let email: String?
}

struct WeightEntry: Codable, Identifiable, Sendable, Equatable {
    let id: Int
    var date: String        // "YYYY-MM-DD" — kept as string to match the API exactly
    var weightKg: Double
    var source: String
    var note: String?

    enum CodingKeys: String, CodingKey {
        case id, date, source, note
        case weightKg = "weight_kg"
    }

    var day: Date {
        Self.dayFormatter.date(from: date) ?? .distantPast
    }

    static let dayFormatter: DateFormatter = {
        let f = DateFormatter()
        f.dateFormat = "yyyy-MM-dd"
        f.timeZone = .current
        f.locale = Locale(identifier: "en_US_POSIX")
        return f
    }()
}

struct WeightStats: Codable, Sendable {
    let count: Int
    let firstDate: String?
    let latestDate: String?
    let startWeightKg: Double?
    let latestWeightKg: Double?
    let minWeightKg: Double?
    let maxWeightKg: Double?
    let totalChangeKg: Double?
    let movingAvg7dKg: Double?
    let avgWeeklyChangeKg: Double?

    enum CodingKeys: String, CodingKey {
        case count
        case firstDate = "first_date"
        case latestDate = "latest_date"
        case startWeightKg = "start_weight_kg"
        case latestWeightKg = "latest_weight_kg"
        case minWeightKg = "min_weight_kg"
        case maxWeightKg = "max_weight_kg"
        case totalChangeKg = "total_change_kg"
        case movingAvg7dKg = "moving_avg_7d_kg"
        case avgWeeklyChangeKg = "avg_weekly_change_kg"
    }
}

struct Goal: Codable, Sendable, Equatable {
    let id: Int
    let targetWeightKg: Double
    let startWeightKg: Double
    let targetDate: String?

    enum CodingKeys: String, CodingKey {
        case id
        case targetWeightKg = "target_weight_kg"
        case startWeightKg = "start_weight_kg"
        case targetDate = "target_date"
    }
}

struct GoalProgress: Codable, Sendable, Equatable {
    let goal: Goal
    let currentWeightKg: Double?
    let lostKg: Double?
    let remainingKg: Double?
    let percentComplete: Double?

    enum CodingKeys: String, CodingKey {
        case goal
        case currentWeightKg = "current_weight_kg"
        case lostKg = "lost_kg"
        case remainingKg = "remaining_kg"
        case percentComplete = "percent_complete"
    }
}
