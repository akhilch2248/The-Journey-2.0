//
//  LoginView.swift
//  The Journey
//
//  DEV MODE sign-in: any account name becomes its own private account.
//  Step 10 swaps this for Sign in with Apple / GoogleSignIn SDKs.
//

import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var store: AppStore
    @State private var identity = ""
    @State private var showServerField = false
    @State private var busy = false

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            Image(systemName: "chart.line.downtrend.xyaxis")
                .font(.system(size: 40, weight: .medium))
                .foregroundStyle(.green)
                .padding(.bottom, 14)

            Text("The Journey")
                .font(.title.weight(.semibold))
            Text("Track your weight. See the trend, not the noise.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.top, 4)

            VStack(alignment: .leading, spacing: 8) {
                Text("Account name")
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(.secondary)
                TextField("akhil", text: $identity)
                    .textFieldStyle(.roundedBorder)
                    #if os(iOS)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    #endif
                Text("Dev mode. Any name works and becomes its own private account.")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            .padding(.top, 28)

            if let error = store.errorMessage {
                Text(error)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .padding(.top, 8)
            }

            VStack(spacing: 10) {
                signInButton("Continue with Apple", systemImage: "apple.logo", provider: "apple")
                signInButton("Continue with Google", systemImage: "g.circle", provider: "google")
            }
            .padding(.top, 20)

            Spacer()

            DisclosureGroup("Server", isExpanded: $showServerField) {
                TextField("http://127.0.0.1:8003", text: store.$apiBase)
                    .textFieldStyle(.roundedBorder)
                    #if os(iOS)
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    #endif
                    .padding(.top, 6)
                Text("On a physical device, use your Mac's LAN address.")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .font(.footnote)
            .tint(.secondary)
        }
        .padding(28)
        .frame(maxWidth: 420)
    }

    private func signInButton(_ title: String, systemImage: String, provider: String) -> some View {
        Button {
            busy = true
            Task {
                await store.signIn(provider: provider, devToken: identity.trimmingCharacters(in: .whitespaces))
                busy = false
            }
        } label: {
            Label(title, systemImage: systemImage)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 6)
        }
        .buttonStyle(.bordered)
        .disabled(identity.trimmingCharacters(in: .whitespaces).isEmpty || busy)
    }
}
