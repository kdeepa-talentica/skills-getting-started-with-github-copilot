"""
Tests for the FastAPI application endpoints
"""
import pytest


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root path redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test getting all activities returns 200 and correct data"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # We have 9 activities
        
        # Check that Chess Club exists with correct structure
        assert "Chess Club" in data
        assert "description" in data["Chess Club"]
        assert "schedule" in data["Chess Club"]
        assert "max_participants" in data["Chess Club"]
        assert "participants" in data["Chess Club"]
    
    def test_activities_have_correct_fields(self, client):
        """Test that each activity has all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in data.items():
            for field in required_fields:
                assert field in activity_data, f"{activity_name} missing {field}"
            
            # Validate data types
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify the participant was actually added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_for_nonexistent_activity(self, client):
        """Test signup for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_participant(self, client):
        """Test that a student cannot sign up twice for the same activity"""
        email = "duplicate@mergington.edu"
        activity = "Chess Club"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_with_url_encoded_activity_name(self, client):
        """Test signup with URL-encoded activity name (spaces)"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=coder@mergington.edu"
        )
        assert response.status_code == 200
    
    def test_signup_with_special_characters_in_email(self, client):
        """Test signup with special characters in email"""
        response = client.post(
            "/activities/Chess Club/signup?email=test.user%2Bfilter@mergington.edu"
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Tests for DELETE /activities/{activity_name}/participant endpoint"""
    
    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        # First, add a participant
        email = "toremove@mergington.edu"
        activity = "Chess Club"
        
        client.post(f"/activities/{activity}/signup?email={email}")
        
        # Now remove them
        response = client.delete(
            f"/activities/{activity}/participant?email={email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify the participant was actually removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]
    
    def test_remove_existing_participant(self, client):
        """Test removing a participant that was already in the initial data"""
        activity = "Chess Club"
        email = "michael@mergington.edu"  # This email is in initial data
        
        # Verify participant exists
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]
        
        # Remove participant
        response = client.delete(
            f"/activities/{activity}/participant?email={email}"
        )
        assert response.status_code == 200
        
        # Verify removal
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]
    
    def test_remove_participant_from_nonexistent_activity(self, client):
        """Test removing a participant from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Activity/participant?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_remove_nonexistent_participant(self, client):
        """Test removing a participant that isn't registered"""
        response = client.delete(
            "/activities/Chess Club/participant?email=notregistered@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_remove_participant_with_url_encoded_activity(self, client):
        """Test removing participant with URL-encoded activity name"""
        # Add a participant first
        email = "urltest@mergington.edu"
        client.post("/activities/Programming%20Class/signup?email=" + email)
        
        # Remove with URL encoding
        response = client.delete(
            f"/activities/Programming%20Class/participant?email={email}"
        )
        assert response.status_code == 200


class TestIntegrationScenarios:
    """Integration tests for combined operations"""
    
    def test_signup_and_remove_workflow(self, client):
        """Test complete workflow: signup -> verify -> remove -> verify"""
        activity = "Drama Club"
        email = "workflow@mergington.edu"
        
        # 1. Get initial state
        response = client.get("/activities")
        initial_count = len(response.json()[activity]["participants"])
        
        # 2. Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # 3. Verify signup
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count + 1
        assert email in response.json()[activity]["participants"]
        
        # 4. Remove participant
        remove_response = client.delete(f"/activities/{activity}/participant?email={email}")
        assert remove_response.status_code == 200
        
        # 5. Verify removal
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == initial_count
        assert email not in response.json()[activity]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test that a student can sign up for multiple different activities"""
        email = "multisport@mergington.edu"
        activities = ["Chess Club", "Swimming Club", "Art Studio"]
        
        for activity in activities:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify student is in all activities
        response = client.get("/activities")
        all_activities = response.json()
        
        for activity in activities:
            assert email in all_activities[activity]["participants"]
    
    def test_activity_capacity_tracking(self, client):
        """Test that participant count updates correctly"""
        activity = "Chess Club"
        
        # Get initial count
        response = client.get("/activities")
        initial_participants = len(response.json()[activity]["participants"])
        max_participants = response.json()[activity]["max_participants"]
        
        # Add participants up to capacity
        spots_available = max_participants - initial_participants
        
        for i in range(min(3, spots_available)):  # Add up to 3 more participants
            email = f"student{i}@mergington.edu"
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify count
        response = client.get("/activities")
        final_participants = len(response.json()[activity]["participants"])
        expected_count = initial_participants + min(3, spots_available)
        assert final_participants == expected_count
