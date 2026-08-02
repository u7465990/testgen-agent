package com.demo;

import com.demo.PasswordValidator;
import org.junit.Assert;
import org.junit.Test;

public class PasswordValidator_strength_Str_Test_Boundary_31 {


    @Test
    public void strengthWithNullReturnsWeak() {
        PasswordValidator validator = new PasswordValidator();
        Assert.assertEquals("weak", validator.strength(null));
    }

}
