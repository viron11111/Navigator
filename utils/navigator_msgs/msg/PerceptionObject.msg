std_msgs/Header header            # Stamped with the time of the last sighting of the buoy

string name 					  # Name of object

#Constant Standard names to use
string DETECT_DELIVER_PLATFORM=shooter
string IDENTIFY_AND_DOCK=dock
string SCAN_THE_CODE=scan_the_code
string TOTEM=totem
string START_GATE_BUOY=start_gate
string BUOY=buoy
string UNKNOWN=unknown
string ALL=all

geometry_msgs/Point position      # Estimated position of the buoy stamped (in the frame of the header)

uint32 id                         # If we want to label each buoy and keep track of it
uint8 confidence                  # 0-255 how confident are we that this is a buoy
geometry_msgs/Vector3 size		  # Object size in x,y,z

geometry_msgs/Point32[] points    # Points (in ENU frame) that belong to the buoy
uint32[] intensity				  # Track intesnity values for each lidar point
uint32 pclInliers				  # Track inliers found for pcl plane fitting algorithm
geometry_msgs/Vector3 normal	  # Unit vector for normal to one of the vertical planes of the object
std_msgs/ColorRGBA color         # Average (?) color of the buoy
